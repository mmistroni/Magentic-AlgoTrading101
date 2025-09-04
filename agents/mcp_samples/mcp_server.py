#https://martinfowler.com/articles/function-call-LLM.html?utm_source=www.pythonweekly.com&utm_medium=newsletter&utm_campaign=python-weekly-issue-698-may-8-2025&_bhlid=f944725abe32d871b0b01da685a24e6396fdb57b#ScaffoldOfATypicalAgent
from .mcp_schemas import CLARIFY_SCHEMA, PRODUCT_DETAILS_SCHEMA, SEARCH_SCHEMA
from .mcp_models import SearchClient, 
import json
import requests


TOOL_REGISTRY = {
    "search_products": SEARCH_SCHEMA,
    "get_product_details": PRODUCT_DETAILS_SCHEMA,
    "clarify": CLARIFY_SCHEMA
}

@app.route("/tools", methods=["GET"])
def get_tools():
    return jsonify(list(TOOL_REGISTRY.values()))

@app.route("/invoke/search_products", methods=["POST"])
def search_products():
    data = request.json
    keywords = data.get("keywords")
    search_results = SearchClient().search(keywords)
    return jsonify({"response": f"Here are the products I found: {', '.join(search_results)}"}) 

@app.route("/invoke/get_product_details", methods=["POST"])
def get_product_details():
    data = request.json
    product_id = data.get("product_id")
    product_details = SearchClient().get_product_details(product_id)
    return jsonify({"response": f"{product_details['name']}: price: ${product_details['price']} - {product_details['description']}"})

@app.route("/invoke/clarify", methods=["POST"])
def clarify():
    data = request.json
    question = data.get("question")
    return jsonify({"response": question})

if __name__ == "__main__":
    app.run(port=8000)