import random
import datetime

def log_random_event():
    events = ["User joined", "Payment received", "Membership expired", "Bot started", "Error occurred"]
    event = random.choice(events)
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] {event}")

if __name__ == "__main__":
    log_random_event()
