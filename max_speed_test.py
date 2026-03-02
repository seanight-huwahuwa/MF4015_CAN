import can
import time

class MotorSpeedTester:
    def __init__(self, channel, motor_id=1):
        self.bus = can.interface.Bus(interface='slcan', channel=channel, ttyBaudrate=1000000, bitrate=1000000)
        self.can_id = 0x140 + motor_id
        self.current_speed_rpm = 0.0

    def stop_motor(self):
        cmd = [0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command("Stop Motor", cmd)

    def set_speed_rpm(self, speed_rpm):
        speed_dps = speed_rpm * 360.0 / 60.0
        speed_lsb = int(speed_dps * 100)
        speed_bytes = speed_lsb.to_bytes(4, byteorder='little', signed=True)
        
        cmd = [0xA2, 0x00, 0x00, 0x00, speed_bytes[0], speed_bytes[1], speed_bytes[2], speed_bytes[3]]
        self._send_command(f"Set Target: {speed_rpm} RPM", cmd)

    def _send_command(self, action_name, data):
        msg = can.Message(arbitration_id=self.can_id, data=data, is_extended_id=False)
        self.bus.send(msg)
        
        response = self.bus.recv(1.0)
        if response and response.data[0] == 0xA2:
            # 0xA2 Command Response Parsing
            # Data[4:6] holds Speed in DPS
            speed_dps = int.from_bytes(response.data[4:6], byteorder='little', signed=True)
            self.current_speed_rpm = speed_dps * 60.0 / 360.0
            
            # Data[2:4] holds IQ Current in 0.01A/LSB
            iq_current = int.from_bytes(response.data[2:4], byteorder='little', signed=True) * 0.01
            
            # Error checking could be added by sending 0x9A occasionally, but we'll monitor speed here.
            print(f"[{action_name}] Measured => Speed: {self.current_speed_rpm:.1f} RPM | Current: {iq_current:.2f} A")

    def shutdown(self):
        self.stop_motor()
        self.bus.shutdown()

def main():
    tester = MotorSpeedTester(channel='/dev/cu.usbmodem2089337D36301')
    try:
        print("====================================")
        print("Starting Motor Speed Limit Test...")
        print("CAUTION: SECURE THE MOTOR FIRMLY!")
        print("Press Ctrl+C at any time to EMERGENCY STOP!\n")
        print("====================================")
        
        # Test targets in RPM increments
        test_rpms = [100, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000]
        
        for tgt_rpm in test_rpms:
            print(f"\n--- Testing Target: {tgt_rpm} RPM ---")
            
            # Run at target RPM 
            tester.set_speed_rpm(tgt_rpm)
            time.sleep(1.5) # Wait for acceleration
            
            # Read back multiple times to see if it stabilized
            for _ in range(3):
                tester.set_speed_rpm(tgt_rpm) 
                time.sleep(0.5)
                
            # Check if measured speed aligns with target speed
            # If measured is significantly lower, motor maxed out its physical limit
            if tester.current_speed_rpm < (tgt_rpm * 0.8) and tgt_rpm > 500:
                print(f"\n=> ALERT: Target was {tgt_rpm} RPM, but max reached is approx {tester.current_speed_rpm:.1f} RPM.")
                print("Likely reached mechanical, voltage, or current limit.")
                break
                
        print("\nTest Sequence Completed.")
        
    except KeyboardInterrupt:
        print("\n[!] Emergency Stop requested by User!")
    finally:
        print("\nStopping motor and closing CAN bus...")
        tester.shutdown()
        print("Safely Shut Down.")

if __name__ == "__main__":
    main()
