import asyncio
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup, Tag
from Main.Repositry.redis.redis_config import add_to_set, is_member
from Main.Repositry.db.db_config import execute_query 
from Main.Repositry.celery.celery_config import app


class ManageHeadlessBrowser:

    @staticmethod
    async def launch_browser():
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        return playwright, browser


class LinkMethods:

    @staticmethod
    def is_valid_href(href: str) -> bool:
        return bool(href and not href.startswith("#"))

    @staticmethod
    def normalize_url(base_url: str, href: str) -> str:
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        cleaned_path = parsed.path.rstrip('/')
        return parsed._replace(path=cleaned_path).geturl()

    @staticmethod
    def extract_href_and_text(a_tag: Tag) -> tuple[str, str]:
        href = a_tag.get('href', '').strip()
        text = a_tag.get_text(strip=True)
        return href, text


class ExtractLink:

    def __init__(self, url_list: list, concurrent_limit: int = 10):
        self.concurrent_limit = concurrent_limit
        self.url_list = url_list

    async def extract_links_from_page(self, page, url: str) -> list:
        try:
            print(f"Visiting: {url}")
            await page.goto(url, wait_until="networkidle", timeout=45000)
        except PlaywrightTimeoutError:
            print(f"[WARN] Timeout while trying to load: {url}")
            return []

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        seen = set()
        links = []

        for a_tag in soup.find_all('a', href=True):
            href, text = LinkMethods.extract_href_and_text(a_tag)

            if not LinkMethods.is_valid_href(href):
                continue

            cleaned_url = LinkMethods.normalize_url(url, href)

            if cleaned_url not in seen:
                seen.add(cleaned_url)
                links.append({'href': cleaned_url, 'text': text})

        return links

    async def scrape_with_pool(self):
        playwright, browser = await ManageHeadlessBrowser.launch_browser()
        context = await browser.new_context()
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def process_url(url):
            async with semaphore:
                page = await context.new_page()
                result = await self.extract_links_from_page(page, url)
                await page.close()
                return result

        tasks = [process_url(url) for url in self.url_list]
        results = await asyncio.gather(*tasks)

        await context.close()
        await browser.close()
        await playwright.stop()

        return results

class ManageExtractedLink:

    PRODUCT_URL_PATTERNS = [
        '/product/', '/item/', '/p/', '/products/', '/shop/', '/buy/', '/detail/'
    ]

    @staticmethod
    def process(job_payload):
        print(job_payload)

        if is_member(job_payload['website_redis_set'], job_payload['url']):
            print(f"[SKIP] URL already processed: {job_payload['url']}")
            return

        add_to_set(job_payload['website_redis_set'], job_payload['url'])

        if job_payload['depth_score'] < 5:
            payload = {
                'url': job_payload['url'],
                'website_redis_set': job_payload['website_redis_set'],
                'website_url_id': job_payload['website_url_id'],
                'depth_score': job_payload['depth_score'] + 1
            }
            process_job.delay(payload)

        ManageExtractedLink.__add_to_db(job_payload['url'], job_payload['website_url_id'])

    @staticmethod
    def __add_to_db(url: str, website_url_id: int):
        if ManageExtractedLink.__is_product_url(url):
            print(f"[DB] Storing product URL: {url}")
            execute_query(
                "INSERT INTO scraped_product_url (website_url_id, product_url) VALUES (%s, %s)",
                (website_url_id, url)
            )
        else:
            print(f"[SKIP] URL does not match product pattern: {url}")

    @staticmethod
    def __is_product_url(url: str) -> bool:
        lower_url = url.lower()
        return any(pattern in lower_url for pattern in ManageExtractedLink.PRODUCT_URL_PATTERNS)


@app.task(name="scraper.process_job")
def process_job(job_details):
    url = job_details['url']
    scraper = ExtractLink([url])
    results = asyncio.run(scraper.scrape_with_pool())

    print(f"[DONE] URL: {url} -> Found {len(results[0])} links")
    for link in results[0]:
        print(f"- {link['href']} (text: {link['text']})")
        ManageExtractedLink.process({'url': link['href'], 'website_url_id': job_details['website_url_id'], 'website_redis_set': job_details['website_redis_set'], 'depth_score': job_details['depth_score']});

    return results[0]
