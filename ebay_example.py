"""Example: search eBay watch listings using the official Browse API."""

from ebay_client import EbayClient


def main():
    client = EbayClient()
    for item in client.search("Rolex DateJust"):
        price = item.get("price", {})
        print(f"{item['title']} - {price.get('value')} {price.get('currency')} - {item['itemWebUrl']}")


if __name__ == "__main__":
    main()
