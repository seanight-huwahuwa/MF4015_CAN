import can
import time
import struct

class MyActuatorController:
    def __init__(self, channel, motor_id=1):
        self.bus = can.interface.Bus(interface='slcan', channel=channel, ttyBaudrate=1000000, bitrate=1000000)
        self.motor_id = motor_id
        self.can_id = 0x140 + motor_id
        print(f"Connected to CAN bus, controlling motor ID {motor_id} (CAN ID: {hex(self.can_id)})")

    def stop_motor(self):
        # 0x81: Motor Stop Command
        cmd = [0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command("Stop Motor", cmd)

    def set_speed(self, speed_dps):
        # 0xA2: Speed Closed-Loop Control Command
        # speed_dps is actual speed in degree/sec.
        # Control value speedControl is int32_t, 0.01dps/LSB -> speed * 100
        speed_lsb = int(speed_dps * 100)
        speed_bytes = speed_lsb.to_bytes(4, byteorder='little', signed=True)
        
        cmd = [0xA2, 0x00, 0x00, 0x00, speed_bytes[0], speed_bytes[1], speed_bytes[2], speed_bytes[3]]
        self._send_command(f"Set Speed ({speed_dps} dps)", cmd)

    def set_position_absolute(self, angle_degree, max_speed_dps):
        # 0xA4: Absolute Position Closed-Loop Control Command
        # angle_degree: 0.01degree/LSB -> angle * 100 (int32_t)
        # max_speed_dps: 1dps/LSB -> int (uint16_t)
        
        angle_lsb = int(angle_degree * 100)
        angle_bytes = angle_lsb.to_bytes(4, byteorder='little', signed=True)
        
        speed_lsb = int(max_speed_dps)
        speed_bytes = speed_lsb.to_bytes(2, byteorder='little', signed=False)

        cmd = [0xA4, 0x00, speed_bytes[0], speed_bytes[1], angle_bytes[0], angle_bytes[1], angle_bytes[2], angle_bytes[3]]
        self._send_command(f"Set Absolute Position ({angle_degree} deg, max {max_speed_dps} dps)", cmd)

    def _send_command(self, action_name, data):
        msg = can.Message(arbitration_id=self.can_id, data=data, is_extended_id=False)
        print(f"\n[{action_name}] Sending: {[hex(d) for d in data]}")
        self.bus.send(msg)
        
        response = self.bus.recv(1.0)
        if response:
            self._parse_response(response)
        else:
            print(f"[{action_name}] No response received.")

    def _parse_response(self, response):
        cmd_byte = response.data[0]
        print(f"Received Response from {hex(response.arbitration_id)}: {[hex(d) for d in response.data]}")
        
        if cmd_byte in [0xA2, 0xA4]:
            # Same parsing logic for replies from control commands
            temperature = response.data[1]
            iq_current = int.from_bytes(response.data[2:4], byteorder='little', signed=True) * 0.01
            speed = int.from_bytes(response.data[4:6], byteorder='little', signed=True)
            encoder = int.from_bytes(response.data[6:8], byteorder='little', signed=True)
            print(f"Status - Temp: {temperature} C, iq_current: {iq_current:.2f} A, Speed: {speed} dps, Angle: {encoder}")
        elif cmd_byte in [0x81]:
            print("Status - Motor Stopped.")

    def shutdown(self):
        self.stop_motor()
        self.bus.shutdown()
        print("CAN bus connection closed.")

def main():
    # USB Serial port may be different, change it if necessary
    PORT = '/dev/cu.usbmodem2089337D36301' 
    controller = MyActuatorController(channel=PORT, motor_id=1)
    
    try:
        # Example 1: Speed Control sequence
        print("\n--- Testing Speed Control ---")
        controller.set_speed(100) # 100 dps
        time.sleep(2)
        controller.set_speed(-100) # Reverse 100 dps
        time.sleep(2)
        controller.stop_motor()
        time.sleep(1)

        # Example 2: Absolute Position Control Sequence
        print("\n--- Testing Absolute Position Control ---")
        controller.set_position_absolute(360.0, 150) # Go to 360 degrees at 150 dps speed limit
        time.sleep(3)
        controller.set_position_absolute(0.0, 150) # Return to 0 degrees
        time.sleep(3)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        controller.shutdown()

if __name__ == "__main__":
    main()