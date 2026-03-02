import can
import time

def main():
    try:
        # Mac에서 CANable V2 (slcan 펌웨어 사용) 의 경우 포트 경로를 정확하게 확인해야 합니다.
        # 보통 /dev/cu.usbmodemXXXXX 형식으로 잡힙니다.
        # slcan 인터페이스를 사용하여 생성합니다. 통신 속도가 1M(1000000)인지 500k(500000)인지 모터 스펙과 맞게 설정하세요.
        # 일반적으로 MyActuator 모터의 기본 CAN baudrate는 1M(1000000) 또는 500k 입니다. (자세한 건 매뉴얼 참조)
        bus = can.interface.Bus(interface='slcan', channel='/dev/cu.usbmodem2089337D36301', ttyBaudrate=1000000, bitrate=1000000)
        print("Connected to CAN bus")

        # 명령: 0x9A (Read Motor Status 1 and Error Flag Command)
        # ID: 기본적으로 MyActuator 모터의 ID는 1일 때, CAN ID는 0x140 + ID = 0x141 입니다.
        motor_id = 1
        can_id = 0x140 + motor_id
        
        # 0x9A 명령어 구성: [0x9A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        data_9a = [0x9A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        msg_9a = can.Message(arbitration_id=can_id, data=data_9a, is_extended_id=False)
        
        print(f"Sending 0x9A command to ID {hex(can_id)}: {[hex(d) for d in data_9a]}")
        bus.send(msg_9a)
        
        # 응답 대기
        response = bus.recv(1.0)
        if response:
            print(f"Received Response for 0x9A from ID {hex(response.arbitration_id)}: {[hex(d) for d in response.data]}")
            # 데이터 파싱
            if response.data[0] == 0x9A:
                temperature = response.data[1]
                voltage = (response.data[5] << 8 | response.data[4]) * 0.1
                error_state = response.data[7] << 8 | response.data[6]
                print(f"Motor Status 1 - Temp: {temperature} C, Voltage: {voltage:.1f} V, Error State: {hex(error_state)}")
        else:
            print("No response received for 0x9A.")

        # 명령: 0x9C (Read Motor Status 2) -> 온도, 전압(토크), 속도, 위치 등
        data_9c = [0x9C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        msg_9c = can.Message(arbitration_id=can_id, data=data_9c, is_extended_id=False)
        
        print(f"\nSending 0x9C command to ID {hex(can_id)}: {[hex(d) for d in data_9c]}")
        bus.send(msg_9c)

        # 응답 대기
        response = bus.recv(1.0)
        if response:
            print(f"Received Response for 0x9C from ID {hex(response.arbitration_id)}: {[hex(d) for d in response.data]}")
            if response.data[0] == 0x9C:
                temperature = response.data[1]
                iq_current = int.from_bytes(response.data[2:4], byteorder='little', signed=True)
                speed = int.from_bytes(response.data[4:6], byteorder='little', signed=True)
                encoder = int.from_bytes(response.data[6:8], byteorder='little', signed=True)
                print(f"Motor Status 2 - Temp: {temperature} C, iq_current: {iq_current}, Speed: {speed} dps, Motor Angle: {encoder}")
        else:
            print("No response received for 0x9C.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'bus' in locals():
            bus.shutdown()
            print("CAN bus connection closed.")

if __name__ == "__main__":
    main()
