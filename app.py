from flask import Flask, request, jsonify
from Main.Repositry.db.db_config import execute_query
from Main.scraper import process_job

app = Flask(__name__)


@app.route('/create', methods=['POST'])
def create_website_url():
    data = request.get_json()
    website_url = data.get('website_url')

    if not website_url:
        return jsonify({'error': 'website_url is required'}), 400

    existing = execute_query("SELECT id FROM website_url WHERE website_url = %s", (website_url,))
    if existing:
        return jsonify({'error': 'Website URL already exists'}), 400

    execute_query("INSERT INTO website_url (website_url) VALUES (%s)", (website_url,))
    new_id = execute_query("SELECT LAST_INSERT_ID() as id")[0]["id"]

    return jsonify({'message': 'Website URL added', 'id': new_id}), 201


@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_website_url(id):
    result = execute_query("SELECT id FROM website_url WHERE id = %s", (id,))
    if not result:
        return jsonify({'error': 'Website URL not found'}), 404

    execute_query("DELETE FROM scraped_product_url WHERE website_url_id = %s", (id,))
    execute_query("DELETE FROM website_url WHERE id = %s", (id,))
    return jsonify({'message': 'Website URL and associated products deleted'})


@app.route('/generate_product_url/<int:id>', methods=['POST'])
def generate_product_url(id):
    result = execute_query("SELECT website_url FROM website_url WHERE id = %s", (id,))
    if not result:
        return jsonify({'error': 'Website URL not found'}), 404

    url = result[0]["website_url"]
    process_job.delay({
        'url': url,
        'website_url_id': id,
        'depth_score': 0,
        'website_redis_set': f'website_redis_set_key_{id}'
    })

    return jsonify({'message': 'Job queued successfully'})


if __name__ == '__main__':
    app.run(debug=True)
