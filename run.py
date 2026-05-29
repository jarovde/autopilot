"""
Main entrypoint — called by GitHub Actions every week.
Picks next unpublished topic, generates article, publishes, updates state.
"""
import sys
from pipeline.topics import TOPICS, AFFILIATE_LINKS
from pipeline.state import next_topic, mark_published
from pipeline.generate import generate_article
from pipeline.publish import publish


def main():
    topic = next_topic(TOPICS)
    if topic is None:
        print("All topics published. Add more to pipeline/topics.py")
        sys.exit(0)

    print(f"Generating: {topic}")
    article = generate_article(topic, AFFILIATE_LINKS)
    print(f"Title: {article['title']}")
    print(f"Tags: {article['tags']}")

    result = publish(
        title=article["title"],
        body=article["body"],
        tags=article["tags"],
        published=True,
    )
    mark_published(topic)
    print(f"Published: {result['url']}")


if __name__ == "__main__":
    main()
