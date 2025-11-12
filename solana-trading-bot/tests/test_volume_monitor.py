from monitoring.volume_monitor import VolumeMonitor

def test_volume_monitor():
    volume_monitor = VolumeMonitor()

    # Simulate a volume update with the correct key
    volume_data = {
        "token_address": "SOL",  # Use the correct key
        "volume": 1000000,
        "price": 100.50,
        "change": 5.25
    }

    try:
        volume_monitor.update_volumes(volume_data)
        print("Volume data updated successfully")
    except Exception as e:
        print("Failed to update volume data.")
        print(f"Error: {e}")

    # Optionally, test the threshold check
    try:
        threshold_passed = volume_monitor.check_volume_threshold(volume_data)
        print(f"Threshold check passed: {threshold_passed}")
    except Exception as e:
        print("Failed to check volume threshold.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_volume_monitor()