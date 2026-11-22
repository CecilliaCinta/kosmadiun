from groq import Groq
from django.conf import settings
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

client = Groq(api_key=settings.GROQ_API_KEY)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Halo, perkenalkan dirimu sebagai asisten rekomendasi kos Madiun."
        }
    ]
)

print(response.choices[0].message.content)