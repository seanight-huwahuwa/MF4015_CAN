# MyActuator MF4015 CAN Control (Python)

**MyActuator MF4015v2 (RMD-L-4015) 다이렉트 드라이브 BLDC 모터**를 제어하기 위한 파이썬 기반의 CAN 통신 및 제어 인터페이스입니다. 이 프로젝트는 기존 UART/RS485 방식의 한계를 넘어, CANable V2.0 Pro S 어댑터를 활용해 CAN 통신(1Mbps)이 제공하는 최고 속도 및 다축 제어 성능을 완벽히 이끌어내는 것을 목표로 합니다.

## 🚀 주요 기능 (Key Features)

* **완전한 파이썬 모듈화 (`myactuator_motor.py`)**: CAN 버스(`slcan`) 위에서 MyActuator V4.2 프로토콜을 구현한 통합 래퍼(Wrapper) 클래스.
* **직접 하드웨어 제어 (Direct Hardware Control)**:
  * 위치 제어 (`0xA4`): 한 치의 오차 없는 고속 하드웨어 PID 루프 추종.
  * 폐루프 토크 제어 (`0xA1`): 실시간 다이내믹 전류(Current) 조작.
* **가상 임피던스 제어 (Virtual Impedance Control)**: 56-bit Multi-turn 절대 각도 파싱 데이터를 기반으로 한 정밀한 소프트웨어 수준의 스프링-댐퍼(Spring-Damper) 메커니즘.
* **실시간 Teach & Play UI (`realtime_teach_play.py`)**: 
  * **Teach(티칭)**: 사용자가 손으로 모터를 직접 움직여 궤적을 100Hz로 기록합니다. (다이렉트 드라이브 모터 고유의 *코깅 토크(Cogging Torque)*를 활용한 직관적인 햅틱 피드백).
  * **Play(재생)**: 통신 지연(Jitter)에 의한 덜덜거림을 방지하기 위해 모터 하드웨어 위치 제어를 이용하여 부드럽게 궤적을 보간하며 재생합니다.
  * **실시간 시각화**: `PyQt6` 및 `pyqtgraph`를 활용하여 CAN 제어 루프를 차단(Blocking)하지 않고, 목표 각도(Target)와 실제 각도(Actual)를 실시간 텔레메트리로 표시합니다.

## 🛠 하드웨어 구성 (Hardware Setup)

* **모터**: MyActuator MF4015v2 (0.65N.m, 기어비: 0 - Direct Drive)
* **CAN 인터페이스**: CANable V2.0 Pro S (`slcan` 방식 사용)
* **운영체제**: macOS / Linux (Python 3.11 환경에서 테스트 완료)
* **CAN 통신 설정**: 1Mbps Baudrate

## 📦 설치 및 실행 방법 (Installation & Usage)

1. 가상환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate
```

2. 필수 라이브러리 설치:
```bash
pip install python-can pyserial PyQt6 pyqtgraph numpy
```

3. 실시간 Teach & Play 대시보드 실행:
```bash
python realtime_teach_play.py
```

## ⚠️ 발견된 펌웨어 이슈 및 해결 (Firmware Manual Discrepancies)
제조사에서 제공하는 MyActuator Protocol V4.2 공식 매뉴얼 파일과 실제 출하된 모터(MF4015v2)의 펌웨어 간에 파싱 오류가 있어 본 브랜치에서 이를 해결 및 적용했습니다. 

1. **`0x92` 절대 각도(Multi-turn) 읽기 버그**: 
   * **매뉴얼상 설명**: 응답 데이터의 Data[1]~Data[7] 중 `Data[4]~Data[7]`의 4바이트(32-bit)가 절대 각도를 나타낸다고 명시.
   * **실제 하드웨어 동작**: 32비트 파싱 시 특정 각도에서 값이 비정상적으로 오버플로우되거나 튀는 현상 발생. 
   * **해결 방법**: 역공학 분석 결과, 실제 모터는 `Data[1]~Data[7]` 전체 7바이트를 활용한 **56-bit 정수형 리틀 엔디안** 형식으로 각도를 전송하고 있음을 규명했습니다. (해당 수정 사항은 `myactuator_motor.py` 내 `read_multi_turn_angle()` 에 모두 반영되어 있습니다.)

2. **`0xB2` / `0xB5` 설정 읽기 명령어 무응답**:
   * 매뉴얼상 시스템 버전을 읽는 `0xB2` 명령어 등이 명시되어 있으나, 일부 커스텀 펌웨어/신형 보드에서는 해당 명령어에 응답하지 않는 현상이 있습니다. (제어 명령인 0xA0~0xA4 계열은 정상 동작함)

## 📝 참고 문서 (Background Docs)
이 리포지토리는 V4.2 API 명세 확인을 위해 PDF 매뉴얼을 덤프한 `MF4015.txt` 및 `Motor_Motion_Protocol_V4.2.txt` 문서를 포함하고 있습니다.
