*MY APPROACH*

DB:

1. Table: website_url  -  [ id | website_url ]
2. Table: scraped_product_url - [ website_url_id | product_url  ]

REDIS:

1. List of visited url - [ use SET + higher default reserve ]. Private to queue.
2. visitation_queue - [ website_url_id, scrape_url, depth_score, website_redis_set]. Global Queue

STATIC PAGE DATA: 

1. Look for <a> tags. Either it could be a product or category or link to new page.
    1. if product
        1. Add to redis + db.
    2. if not a product
        1. Add to redis only
        2. Step 1 again within the link.
2. Set a limit for depth_score, to avoid cycles.

HANDLE PAGINATION: 

1. Use playwrite to scroll to paginate more on page.
2. Write a script which i will understand pagination link.

![image](https://github.com/user-attachments/assets/f1ef0862-fd9e-4d33-868b-56096be6748a)
