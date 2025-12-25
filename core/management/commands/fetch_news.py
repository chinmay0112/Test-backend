# your_app_name/management/commands/fetch_news.py

import feedparser
from django.core.management.base import BaseCommand
from datetime import datetime
from time import mktime
# MAKE SURE TO CHANGE 'api' TO YOUR ACTUAL APP NAME
from core.models import CurrentAffair 

class Command(BaseCommand):
    help = 'Fetches latest PIB news via Google News RSS'

    def handle(self, *args, **kwargs):
        url = "https://news.google.com/rss/search?q=site:pib.gov.in+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
        
        self.stdout.write(f"Connecting to: {url}...")
        feed = feedparser.parse(url)
        
        self.stdout.write(f"Found {len(feed.entries)} entries.")

        count = 0
        for entry in feed.entries:
            clean_title = entry.title.rsplit('-', 1)[0].strip()
            
            if CurrentAffair.objects.filter(title=clean_title).exists():
                continue

            published_date = datetime.fromtimestamp(mktime(entry.published_parsed)).date()

            try:
                CurrentAffair.objects.create(
                    title=clean_title,
                    slug=self.generate_slug(clean_title),
                    source_link=entry.link, 
                    source_name="PIB",
                    date=published_date,
                    summary=entry.title,
                    category='NAT',
                    is_published=False
                )
                self.stdout.write(self.style.SUCCESS(f"Saved: {clean_title[:30]}..."))
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving {clean_title}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nTask Complete. Added {count} new articles."))

    def generate_slug(self, title):
        from django.utils.text import slugify
        return slugify(title)[:50]