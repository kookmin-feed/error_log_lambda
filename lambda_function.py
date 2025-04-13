import json
import gzip
import base64
import urllib.request
import os

def lambda_handler(event, context):
    SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

    if not SLACK_WEBHOOK_URL:
        print("❌ SLACK_WEBHOOK_URL is not set!")
        return {'statusCode': 500, 'body': 'Webhook URL not found'}

    # Step 1: 로그 디코딩 및 파싱
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    decompressed_payload = gzip.decompress(compressed_payload)
    logs_data = json.loads(decompressed_payload)

    print("✅ Logs data:", json.dumps(logs_data, indent=2))

    log_group = logs_data.get("logGroup", "-")
    log_stream = logs_data.get("logStream", "-")
    log_events = logs_data.get("logEvents", [])

    if not log_events:
        return {'statusCode': 200, 'body': 'No log events to process'}

    # Step 2: 공통 정보 및 개별 메시지 추출
    common_info = {}
    messages_summary = []

    for log in log_events:
        try:
            parsed = json.loads(log["message"])
            # 최초 1개에서 공통 정보 추출
            if not common_info:
                common_info = {
                    "name": parsed.get("name", "-"),
                    "level": parsed.get("level", "-"),
                    "process": parsed.get("process", "-"),
                    "host": parsed.get("host", "-"),
                    "remoteIp": parsed.get("remoteIp", "-"),
                    "userAgent": parsed.get("userAgent", "-"),
                    "method": parsed.get("method", "-"),
                    "status": parsed.get("status", "-")
                }

            # 요약 메시지 구성
            messages_summary.append(f":clock3: `{parsed.get('timestamp', '-')}` :speech_balloon: `{parsed.get('message', '-')}`")
        except Exception as e:
            messages_summary.append(f":x: 파싱 실패 로그 → {log['message']}")

    # Step 3: Slack 메시지 본문 구성
    slack_text = (
        f":rotating_light: *ERROR 로그 감지됨!*\n"
        f"*Log Group:* `{log_group}`\n"
        f"*Log Stream:* `{log_stream}`\n"
        f"*Log Event Count:* {len(log_events)}\n\n"
        f":name_badge: *name:* `{common_info.get('name', '-')}`\n"
        f":brain: *level:* `{common_info.get('level', '-')}`\n"
        f":1234: *process:* `{common_info.get('process', '-')}`\n"
        f":globe_with_meridians: *host:* `{common_info.get('host', '-')}`\n"
        f"🛜 *remoteIp:* `{common_info.get('remoteIp', '-')}`\n"
        f":receipt: *userAgent:* `{common_info.get('userAgent', '-')}`\n"
        f":satellite_antenna: *method:* `{common_info.get('method', '-')}`\n"
        f":bar_chart: *status:* `{common_info.get('status', '-')}`\n\n"
        f"*🧾 로그 메시지 요약:*\n" + "\n".join(messages_summary)
    )

    # Step 4: Slack 전송
    payload = {"text": slack_text}
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req) as response:
            print("✅ Slack 전송 성공:", response.read())
    except Exception as e:
        print("❌ Slack 전송 실패:", str(e))

    return {'statusCode': 200, 'body': 'Slack 전송 완료'}
