name: Kalam Auto Post

on:
  # Runs 6 times a day (times below are in UTC)
  # 04:00 UTC = 07:00 Saudi/Iraq time
  # 08:00 UTC = 11:00 Saudi/Iraq time
  # 12:00 UTC = 15:00 Saudi/Iraq time
  # 16:00 UTC = 19:00 Saudi/Iraq time
  # 19:00 UTC = 22:00 Saudi/Iraq time
  # 23:10 UTC = 02:10 Saudi/Iraq time (next day)
  schedule:
    - cron: "0 4 * * *"
    - cron: "0 8 * * *"
    - cron: "0 12 * * *"
    - cron: "0 16 * * *"
    - cron: "0 19 * * *"
    - cron: "10 23 * * *"
  # Allows manual run from the Actions tab for testing
  workflow_dispatch:

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run the post script
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHANNEL: ${{ secrets.TELEGRAM_CHANNEL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python post_to_telegram.py
