이 프로젝트는 Mac 환경(macOS)에서 USB-CAN 인터페이스(CANable V2.0 Pro S)를 활용하여 MF4015v2(RMD-L-4015) BLDC 서보 모터를 제어하기 위한 Python 기반 통신 및 제어 시스템입니다. 최상위 목표는 하모닉 드라이브와 결합 가능한 이 고성능 모터의 진정한 "다이렉트 토크 제어(Direct Torque Control)" 및 고속 텔레메트리 성능을 규명하는 것입니다.

## 1. 프로젝트 주요 목표 (Objective)
- 이전 단계의 MKS 모터 한계를 넘고, 진정한 산업용 로봇 관절 모터 수준의 `Virtual Impedance(가상 스프링-댐퍼)` 및 토크 제어(Torque Control) 알고리즘을 파이썬 상에서 구현하고 증명한다.
- 18-bit 인코더 및 CAN Bus(1Mbps) 기반의 초고속, 고정밀 실시간 데이터 수집 및 반영 과정을 검증한다. 

## 2. 개발 단계별 진행 현황 (Phase & Status)

### ✅ Phase 1: 기본 통신 환경 구축 및 상태 확인 (완료)
- [x] venv 가상환경 생성 및 `python-can`, `pyserial` 세팅
- [x] Protocol 매뉴얼 PDF 파싱 텍스트화 (`pdf_to_txt.py` 활용)
- [x] CANable 포트 (`/dev/cu.usbmodem...`) 인식 및 1Mbps 속도 할당
- [x] Read Motor Status 1 (`0x9A`), 2 (`0x9C`) 응답 파싱 및 온도/전류/위치/속도 파싱 검증 완료 (`can_communication.py`)

### ✅ Phase 2: 기본 구동 및 한계 성능 프로파일링 (완료)
- [x] 속도 제어 루프(`0xA2`) 동작 확인 및 양방향 회전 테스트 (`motor_control.py`)
- [x] 절대 위치 제어 한계(`0xA4`) 동작 테스트 완료
- [x] 최대 RPM 탐색 테스트 완료 (`max_speed_test.py`): 현 시스템 허용 전압 조건 하의 무부하 최대 속도(약 1,130 RPM) 구간 규명

### ✅ Phase 3: 라이브러리 모듈화 및 고급 토크 제어 시험 (완료)
- [x] **Python `MyActuator_Motor` 클래스 작성**:
  - 기존 테스트 로직을 재사용 가능한 형태의 독립 파이썬 인터페이스 클래스로 분리.
  - 전송, 수신(데이터 스트리밍 파싱), 안전 셧다운 함수 통합.
  - 시스템 리셋 및 영점 세팅, 브레이크 제어 등 유틸리티 추가 통합.
- [x] **다이렉트 토크 제어 (Closed-loop Torque, `0xA1`) 기능 추가**:
  - 목표 토크(전류) 값 할당 양방향 기능 구현 검증.
- [x] **가상 댐퍼-스프링 임피던스(Virtual Impedance/Compliance) 제어기 완성**:
  - 실시간 Error 포지션을 기반으로 P-gain 모사 복원 토크 인가 로직 구현.
  - 0x9C 응답(Raw Ticks)과 0x92 응답(Degrees)의 유효 해상도 차이를 규명하여 측정 오차 수정.
  - 속도 기반 D-gain 댐핑을 적용하여 복원 후 발생하는 진동(Chattering) 현상 완벽 억제 (100Hz 루프 달성).
  - 동적 목표 지점을 추종하는 '회전식 가상 고무줄(Moving Virtual Spring)' 제어 테스트 성공.

### 📝 Phase 4: 안전 장치 통합 및 응용 제어 어플리케이션 기능 구현 (진행 중)
- [ ] **하드웨어 브레이크 로직 연동**: `0x77`, `0x78` 명령어를 활용한 비상 정지(Virtual/Hardware) 락 제어 테스트
- [ ] **통신 단절 보호 (Watchdog)**: 연결 유실 시 모터의 프리휠(Freewheel) 또는 정지를 유도하는 보호 기능 검증
- [x] **물리적 티치 앤 플레이 (Teach & Play)**: 모터를 손으로 부드럽게 움직여 궤적을 기록(Teach)하고 임피던스 제어로 오차 없이 재생(Play) 성공. (0x92 명령어의 56-bit 절대 각도 데이터 역공학 파싱 적용)
- [x] **실시간 궤적 시각화 및 부드러운 재생 (Real-Time UI & Smooth Play)**: 
  - `PyQt6` 및 `pyqtgraph`를 활용해 Teach/Play 과정과 모터의 실시간 각도를 플로팅하는 대시보드 구축 (`realtime_teach_play.py`).
  - 재생 시 모터 하드웨어 위치 제어(`0xA4`) 명령으로 전환하여 통신 딜레이 없는 최대 성능의 매끄러운 동작 확보.

### 📝 Phase 5: 최종 하드웨어 튜닝 및 문서화 (진행 중)
- [ ] **다축(Multi-Axis) 확장 브레인스토밍**: 향후 다관절 구성을 대비한 복수 모터(CAN ID 관리) 동기화 통신 구조 파악
- [ ] **하드웨어 브레이크 로직 연동**: `0x77`, `0x78` 명령어를 활용한 비상 정지(Virtual/Hardware) 락 제어 테스트
- [ ] **통신 단절 보호 (Watchdog)**: 연결 유실 시 모터의 프리휠(Freewheel) 또는 정지를 유도하는 보호 기능 검증
- [ ] **최종 기술 문서 작성 (ReadMe)**: MF4015(DD 모터) 코깅 토크 특성 등에 관한 물리 피드백 정리 및 사용법 안내

