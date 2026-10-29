import json, logging
from datetime import datetime, timezone
from pathlib import Path

file_path = Path("./data/server-01.jsonl")
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(filename="log_collector.log", encoding="utf-8")
    ]
    )
logger = logging.getLogger(__name__)

def write_logs(read_path, write_path):
    with read_path.open("r", encoding="utf-8") as read_file, open(write_path, "w", encoding="utf-8") as write_file:
        valid_count = 0
        invalid_count = 0

        for line in read_file:
            try:
                tmp = json.loads(line)

                is_valid, reason = validate_log(tmp)

                if not is_valid:
                    logger.warning("Invalid log: %s", reason)
                    invalid_count += 1
                    continue

                valid_count += 1
                write_file.write(json.dumps(tmp) + "\n")

            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON Decode: %s", e)
                invalid_count += 1
                continue

        logger.info("Successfully finished: valid: %d, invalid: %d", valid_count, invalid_count)

def validate_log(log):
    if not isinstance(log, dict):
        return False, "Record must be a JSON object"

    if "username" not in log or not "status" in log:
        return False, "Missing required fields"

    if log["status"] not in {"success", "failure"}:
        return False, "Invalid status"

    return True, ""

def build_s3_key(filename):
    now = datetime.now(timezone.utc)
    date_path = now.strftime("%Y/%m/%d")

    return f"raw-logs/{date_path}/{Path(filename).stem}/{Path(filename).name}"

write_logs(file_path, "log_collector.log")
print(build_s3_key("ejfewqiofjqjfjqoe.log"))