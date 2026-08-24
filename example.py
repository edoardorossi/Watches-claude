"""Example usage of the chrono24 package to search watch listings on chrono24.com."""

import chrono24


def main():
    for listing in chrono24.query("Rolex DateJust").search(limit=10):
        print(listing)


if __name__ == "__main__":
    main()
