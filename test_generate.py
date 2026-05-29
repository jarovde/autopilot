"""Test: generate article and save to file instead of publishing."""
import sys
sys.path.insert(0, ".")
from pipeline.topics import TOPICS, AFFILIATE_LINKS
from pipeline.generate import generate_article

topic = TOPICS[0]
print(f"Topic: {topic}\n")
article = generate_article(topic, AFFILIATE_LINKS)
print(f"Titel: {article['title']}")
print(f"Tags: {article['tags']}")
print(f"\n--- ARTIKEL PREVIEW (eerste 500 tekens) ---\n")
print(article["body"][:500])
print("\n...")

with open("test_output.md", "w") as f:
    f.write(f"# {article['title']}\n\n")
    f.write(article["body"])
print("\nVolledig artikel opgeslagen in: test_output.md")
