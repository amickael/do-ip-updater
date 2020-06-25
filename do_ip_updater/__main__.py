import os
import time
import logging
import re

import digitalocean
from digitalocean.Record import Record
import dotenv
import ipinfo

# Configure logging
logging.basicConfig(
    format="%(levelname)s : %(asctime)s : %(message)s", level=logging.INFO
)

# Load environment, raise error if not specified
if os.path.isfile("../.env"):
    dotenv.load_dotenv()
DO_TOKEN = os.getenv("DO_TOKEN")
DO_DOMAIN = os.getenv("DO_DOMAIN")
IP_TOKEN = os.getenv("IP_TOKEN")
if not bool(DO_TOKEN and DO_DOMAIN):
    logging.error("DO_TOKEN and DO_DOMAIN environment variables are required")
    raise SystemExit

# Configure validation
R_IPV4 = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

# Instantiate app
IP_HANDLER = ipinfo.getHandler(IP_TOKEN)
DOMAIN = digitalocean.Domain(token=DO_TOKEN, name=DO_DOMAIN)


def main():
    logging.info("Update started")

    # Try to get current IP
    try:
        ip_address = IP_HANDLER.getDetails().ip
    except Exception as e:
        logging.error(e)
        return None

    # Validate IP address
    if R_IPV4.match(ip_address) is None:
        logging.error(f"{ip_address} is not a valid IP")
        return None
    else:
        logging.info(f"Attempting to set IP address {ip_address}")

    # Try to find existing record
    records = DOMAIN.get_records()
    target_record = None
    for record in records:
        if record.name == "@" and record.type == "A":
            target_record = record
            break

    # If record was found then update
    record_string = ":".join([DO_DOMAIN, "@", "A", ip_address])
    if isinstance(target_record, Record):
        if target_record.data != ip_address:
            try:
                target_record.data = ip_address
                target_record.save()
            except Exception as e:
                logging.error(e)
            else:
                logging.info(f"Successfully updated {record_string}")
        else:
            logging.info("No update needed")
    # Else create the record
    else:
        try:
            DOMAIN.create_new_domain_record(type="A", name="@", data=ip_address)
        except Exception as e:
            logging.error(e)
        else:
            logging.info(f"Successfully created {record_string}")


if __name__ == "__main__":
    # Get poll interval
    poll_interval = os.getenv("POLL_INTERVAL", 3600)
    try:
        poll_interval = int(poll_interval)
    except ValueError:
        logging.error("POLL_INTERVAL must be a valid integer")
        raise SystemExit

    # Run program
    while True:
        main()
        time.sleep(poll_interval)
