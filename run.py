"""
Main entrypoint — called by GitHub Actions every week.
Picks next unpublished topic, generates article, publishes, updates state.
"""
import os
import sys
from pipeline.topics import TOPICS, AFFILIATE_LINKS
from pipeline.state import next_topic, mark_published
from pipeline.generate import generate_article
from pipeline.publish import publish


def main():
    # --dry-run schrijft het artikel naar stdout en publiceert niets. Bedoeld
    # om via workflow_dispatch te draaien: dat is de enige plek waar de
    # GEMINI_API_KEY bestaat, dus zonder deze vlag is de pijplijn alleen te
    # testen door echt te publiceren. Het topic wordt dan ook NIET afgevinkt,
    # zodat de maandagrun hem gewoon nog oppakt.
    dry_run = "--dry-run" in sys.argv

    topic = next_topic(TOPICS)
    if topic is None:
        print("All topics published. Add more to pipeline/topics.py")
        sys.exit(0)

    print(f"Generating: {topic}")
    article = generate_article(topic, AFFILIATE_LINKS)
    print(f"Title: {article['title']}")
    print(f"Tags: {article['tags']}")

    if dry_run:
        print("\n--- DRY RUN — niets gepubliceerd, topic niet afgevinkt ---\n")
        print(article["body"])
        return

    result = publish(
        title=article["title"],
        body=article["body"],
        tags=article["tags"],
        published=True,
    )
    mark_published(topic)
    print(f"Published: {result['url']}")

    # Geef de echte URL door aan de workflow, zodat de Telegram-melding het
    # artikel linkt in plaats van een generieke regel.
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"url={result['url']}\n")


if __name__ == "__main__":
    main()
