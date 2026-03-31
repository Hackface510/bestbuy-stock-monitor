# Best Buy Stock Monitor

Monitor local Best Buy store inventory and get Discord alerts when items come in stock.

## Quick Start

1. **Install**
2. ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

   2. **Configure**
   3. ```bash
      cp .env.example .env
      # Edit .env with your Discord webhook and SKUs
      ```

      3. **Run**
      4. ```bash
         python -m monitor
         ```

         ## Commands

         ```bash
         python -m monitor          # Run continuously
         python -m monitor --once   # Single check and exit
         python -m monitor --status # Show saved state
         ```

         ## Finding SKUs

         Go to bestbuy.com product page. SKU is in the URL:
         `/site/.../6571900.p` -> SKU is `6571900`

         ## Finding Store IDs

         | ID  | Location          |
         |-----|-------------------|
         | 138 | Pinole, CA        |
         | 135 | Pleasant Hill, CA |
         | 324 | Emeryville, CA    |
         | 482 | San Francisco, CA |

         ## Configuration (.env)

         - `DISCORD_WEBHOOK` - Your Discord webhook URL (required)
         - - `BESTBUY_SKUS` - Comma-separated SKUs to monitor
           - - `BESTBUY_STORES` - Comma-separated store IDs
             - - `CHECK_INTERVAL` - Seconds between checks (default: 60)
               - - `COOLDOWN_MINUTES` - Minutes before re-alerting (default: 30)
                 - - `LOG_LEVEL` - Logging level (default: INFO)
                  
                   - ## Requirements
                  
                   - - Python 3.9+
                     - - See `requirements.txt` for dependencies
                      
                       - ## Getting a Discord Webhook
                      
                       - 1. Open your Discord server
                         2. 2. Go to Server Settings > Integrations > Webhooks
                            3. 3. Click "New Webhook" and copy the URL into `.env`
                              
                               4. ## Notes
                              
                               5. This tool is for personal use to monitor product availability.
                               6. State is persisted in `state.json` so cooldowns survive restarts.
