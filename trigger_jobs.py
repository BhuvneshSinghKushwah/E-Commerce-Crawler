import sys
from Main.scraper import process_job

if len(sys.argv) < 2:
    print("Usage: python trigger_jobs.py <URL1> <URL2> ...")
    sys.exit(1)

input_urls = sys.argv[1:]

for url in input_urls:
    process_job.delay({
        'url': url,
        'website_url_id': 1,
        'depth_score': 0,
        'website_redis_set': 'website_redis_set_key_1'
    })

print("Jobs queued successfully!")
