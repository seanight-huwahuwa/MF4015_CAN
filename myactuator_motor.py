import can
import time

class MyActuatorMotor:
    def __init__(self, channel, motor_id=1, bitrate=1000000, bus_type='slcan'):
        """
        MyActuator_Motor 클래스 초기화
        :param channel: USB-CAN 인터페이스 포트 (예: /dev/cu.usbmodem...)
        :param motor_id: 모터의 노드 ID (기본값 1)
        """
        self.motor_id = motor_id
        self.can_id = 0x140 + motor_id
        
        print(f"[Motor Init] Connecting to {channel} at {bitrate} bps...")
        try:
            self.bus = can.interface.Bus(interface=bus_type, channel=channel, ttyBaudrate=1000000, bitrate=bitrate)
            print(f"[Motor Init] Successfully connected to Motor ID {motor_id} (CAN ID: {hex(self.can_id)})")
        except Exception as e:
            print(f"[Motor Init] Failed to connect: {e}")
            self.bus = None

        # 상태 저장용 변수들
        self.state = {
            'temperature': 0,
            'voltage': 0.0,
            'current': 0.0,
            'speed_dps': 0,
            'angle': 0,
            'error_state': 0
        }

    def _send_command(self, data, expect_response=True):
        if not self.bus:
            return None
            
        msg = can.Message(arbitration_id=self.can_id, data=data, is_extended_id=False)
        self.bus.send(msg)
        
        if expect_response:
            expected_cmd = data[0]
            for _ in range(10):
                response = self.bus.recv(0.1)
                if not response:
                    break
                
                # 들어온 응답이 요청한 명령에 대한 것이면 파싱하고 리턴
                if len(response.data) > 0 and response.data[0] == expected_cmd:
                    self._parse_response(response)
                    return response
                else:
                    # 다른 응답일 경우 상태만 캐싱해두고 계속 기다림 (0x92는 여기서 무시됨)
                    self._parse_response(response)
            
        return None

    def _parse_response(self, response):
        if not response or len(response.data) < 1:
            return
            
        cmd = response.data[0]
        
        # 0x9A: 상태 1 (온도, 전압, 에러상태 등)
        if cmd == 0x9A:
            self.state['temperature'] = response.data[1]
            self.state['voltage'] = (response.data[5] << 8 | response.data[4]) * 0.1
            self.state['error_state'] = (response.data[7] << 8 | response.data[6])
            
        # 0x9C, 0xA1, 0xA2, 0xA4, 0xA6, 0xA8: 동작 상태 응답 프레임 형식이 동일함
        # 형태: [CMD, Temp, Iq_L, Iq_H, Speed_L, Speed_H, Angle_L, Angle_H]
        elif cmd in [0x9C, 0xA1, 0xA2, 0xA4, 0xA6, 0xA8]:
            self.state['temperature'] = response.data[1]
            self.state['current'] = int.from_bytes(response.data[2:4], byteorder='little', signed=True) * 0.01  # A 단위
            self.state['speed_dps'] = int.from_bytes(response.data[4:6], byteorder='little', signed=True)      # degree/sec
            
            raw_angle = int.from_bytes(response.data[6:8], byteorder='little', signed=True)          # degree
            self.state['angle'] = raw_angle

    # --- 실시간 상태 읽기 ---
    def read_status_2(self):
        """ 모터 상태 2 읽기 (0x9C) - 현재전류, 속도, 위치 체크 """
        cmd = [0x9C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)
        return self.state

    def read_multi_turn_angle(self):
        """ Read multi-turn angle (0x92) - 32-bit 고정밀 절대 위치 체크 """
        cmd = [0x92, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        if not self.bus:
            return 0.0
            
        msg = can.Message(arbitration_id=self.can_id, data=cmd, is_extended_id=False)
        self.bus.send(msg)
        
        # 수신 버퍼에 다른 명령 응답이 밀려있을 수 있으므로 루프를 돌며 0x92를 찾습니다.
        for _ in range(10):
            response = self.bus.recv(0.1)
            if not response:
                break
            # 만약 다른 응답이면 파싱해서 상태 업데이트 (옵션)
            if response.data[0] != 0x92:
                self._parse_response(response)
                continue
            
            if len(response.data) >= 8 and response.data[0] == 0x92:
                # 0x92 returns 56-bit signed int at index 1:8 (0.01 degree/LSB) based on Protocol 4.2
                angle_lsb = int.from_bytes(response.data[1:8], byteorder='little', signed=True)
                return angle_lsb / 100.0
        return self.state['angle']  # 못 찾은 경우 마지막 상태 복귀, 또는 0.0

    # --- 시스템 및 설정 명령 ---
    def set_current_position_as_zero(self):
        """ 
        [매우 주의] 현재 다회전 모터 위치를 영구 메모리(ROM)에 0도 영점으로 기록합니다. (0x64) 
        이 명령을 내린 후 시스템을 재시작해야 완전히 적용됩니다.
        """
        cmd = [0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)

    def reset_system(self):
        """ 시스템 리셋 (0x76) - 영점 캘리브레이션 등 설정 변경 적용 시 필요 """
        cmd = [0x76, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd, expect_response=False)  # 리셋 시에는 응답이 안 올 수 있음.
        time.sleep(1.0) # 부팅될 때까지 대기

    def release_brake(self):
        """ 시스템 브레이크 해제 (0x77) """
        cmd = [0x77, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)

    def lock_brake(self):
        """ 시스템 브레이크 구속 (0x78) """
        cmd = [0x78, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)

    # --- 제어 명령 ---
    def stop_motor(self):
        """ 모터 정지 및 제어 해제 (0x81) """
        cmd = [0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)
        
    def set_torque(self, iq_current_A):
        """ 
        Torque Closed-Loop 제어 (0xA1)
        :param iq_current_A: 목표 토크(전류) 값. 단위 A (예: 1.5 -> 1.5A)
        """
        iq_lsb = int(iq_current_A * 100) # 0.01A / LSB
        iq_bytes = iq_lsb.to_bytes(2, byteorder='little', signed=True)
        
        cmd = [0xA1, 0x00, 0x00, 0x00, iq_bytes[0], iq_bytes[1], 0x00, 0x00]
        self._send_command(cmd)

    def set_speed(self, speed_dps):
        """ Speed Closed-Loop 제어 (0xA2) """
        speed_lsb = int(speed_dps * 100) # 0.01dps / LSB
        speed_bytes = speed_lsb.to_bytes(4, byteorder='little', signed=True)
        
        cmd = [0xA2, 0x00, 0x00, 0x00, speed_bytes[0], speed_bytes[1], speed_bytes[2], speed_bytes[3]]
        self._send_command(cmd)

    def hold_position(self, max_speed_dps=360):
        """ Incremental Position Closed-Loop 제어 (0xA8)를 활용한 현재 위치 홀딩 (안전함) """
        speed_lsb = int(max_speed_dps)
        speed_bytes = speed_lsb.to_bytes(2, byteorder='little', signed=False)

        # 0만큼 이동하라는 뜻이므로, 타겟 각도는 0
        cmd = [0xA8, 0x00, speed_bytes[0], speed_bytes[1], 0x00, 0x00, 0x00, 0x00]
        self._send_command(cmd)

    def set_absolute_position(self, target_angle, max_speed_dps):
        """ Absolute Position Closed-Loop 제어 (0xA4) """
        angle_lsb = int(target_angle * 100)
        angle_bytes = angle_lsb.to_bytes(4, byteorder='little', signed=True)
        speed_lsb = int(max_speed_dps)
        speed_bytes = speed_lsb.to_bytes(2, byteorder='little', signed=False)

        cmd = [0xA4, 0x00, speed_bytes[0], speed_bytes[1], angle_bytes[0], angle_bytes[1], angle_bytes[2], angle_bytes[3]]
        self._send_command(cmd)

    def shutdown(self):
        """ 셧다운 안전 로직 """
        self.stop_motor() # 정지 명령
        time.sleep(0.1)
        if self.bus:
            self.bus.shutdown()
        print("\n[Motor Power-off] CAN Bus closed.")
