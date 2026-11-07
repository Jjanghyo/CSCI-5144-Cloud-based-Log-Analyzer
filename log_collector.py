import json, logging, boto3, os, botocore
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

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
        return valid_count, invalid_count

def validate_log(log):
    if not isinstance(log, dict):
        return False, "Record must be a JSON object"

    if "username" not in log or not "status" in log:
        return False, "Missing required fields"

    if log["status"] not in {"success", "failure"}:
        return False, "Invalid status"

    if "timestamp" not in log:
        return False, "Missing timestamp"
    
    if "source_ip" not in log:
        return False, "Missing source_ip"
    
    if "event_type" not in log:
        return False, "Missing event_type"

    if "source" not in log:
        return False, "Missing source"

    return True, ""

def build_s3_key(filename):
    now = datetime.now(timezone.utc)
    date_path = now.strftime("%Y/%m/%d")

    return f"raw-logs/{date_path}/{Path(filename).stem}/{Path(filename).name}"

def upload_to_s3(file_path, filename):
    bucket_name = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-2")

    if not bucket_name:
        logger.error("S3_BUCKET environment variable is not set")

    s3 = boto3.client("s3", region_name=region)

    s3_key = build_s3_key(filename)

    try:
        s3.upload_file(
            file_path,
            bucket_name,
            s3_key
        )
        logger.info("Successfully uploaded to S3: %s", s3_key)

    except botocore.exceptions.ClientError as e:
        logger.error("Failed to upload file to S3")
        raise

if __name__ == "__main__":
    data = Path("./data")
    output_dir = Path("./output")
    output_dir.mkdir(parents=True, exist_ok=True)

    valids = 0
    invalids = 0

    for input_path in sorted(data.glob("*.jsonl")):
        file_path = input_path
        output_path = output_dir / input_path.name
        valid_count, invalid_count = write_logs(file_path, output_path)
        valids += valid_count
        invalids += invalid_count

        if valid_count > 0:
            upload_to_s3(output_path, file_path.name)
        else:
            logger.info("No valid logs to upload for %s.", file_path.name)

    logger.info("Total valid logs: %d, Total invalid logs: %d", valids, invalids)
