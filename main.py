import logging
import threading
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('stablecoin_whale_tracker.log')
    ]
)
logger = logging.getLogger(__name__)

def run_stablecoin_tracker():
    """Run the stablecoin tracker in a separate thread."""
    try:
        from stablecoin_tracker import main as stablecoin_main
        logger.info("Starting stablecoin tracker...")
        stablecoin_main()
    except Exception as e:
        logger.error(f"Error in stablecoin tracker: {e}")

def run_whale_tracker():
    """Run the whale tracker in a separate thread."""
    try:
        from whale_tracker import main as whale_main
        logger.info("Starting whale tracker...")
        whale_main()
    except Exception as e:
        logger.error(f"Error in whale tracker: {e}")

def check_api_keys():
    """Verify API keys are properly configured."""
    load_dotenv()
    required_keys = ['ETHERSCAN_API_KEY', 'BSCSCAN_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")
    
    logger.info("API keys verified ✅")

def main():
    try:
        # Check API keys first
        check_api_keys()
        
        # Create and start threads for each tracker
        stablecoin_thread = threading.Thread(target=run_stablecoin_tracker, name="StablecoinTracker")
        whale_thread = threading.Thread(target=run_whale_tracker, name="WhaleTracker")
        
        stablecoin_thread.daemon = True
        whale_thread.daemon = True
        
        logger.info("Starting trackers...")
        stablecoin_thread.start()
        whale_thread.start()
        
        # Keep the main thread alive and monitor the worker threads
        while True:
            if not stablecoin_thread.is_alive():
                logger.error("Stablecoin tracker thread died, restarting...")
                stablecoin_thread = threading.Thread(target=run_stablecoin_tracker, name="StablecoinTracker")
                stablecoin_thread.daemon = True
                stablecoin_thread.start()
            
            if not whale_thread.is_alive():
                logger.error("Whale tracker thread died, restarting...")
                whale_thread = threading.Thread(target=run_whale_tracker, name="WhaleTracker")
                whale_thread.daemon = True
                whale_thread.start()
            
            # Log status every hour
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"[{current_time}] Both trackers running normally ✅")
            
            time.sleep(3600)  # Check status every hour
            
    except KeyboardInterrupt:
        logger.info("Shutting down trackers...")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
    finally:
        logger.info("Tracker shutdown complete")

if __name__ == "__main__":
    main() 