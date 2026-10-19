# Xbox 패드로 FR3 조작

기존 RViz Plan/Execute 실행을 종료하고 이 구성을 단독으로 실행한다.
다른 프로젝트의 joystick_control은 사용하거나 수정하지 않는다.

## 1. Xbox 패드 연결과 인식

처음에는 USB 케이블로 연결한다. 터미널에서:

```bash
source ~/ros2_ws/install/setup.bash
ros2 run joy joy_enumerate_devices
```

목록에 Xbox 패드가 보여야 한다. 여러 패드가 있으면 아래 실행 명령에 `device_id:=번호`를 추가한다.
설정은 joy_node의 일반적인 Xbox 축 배치(왼쪽 0/1, 오른쪽 3/4, LB=4, RB=5, B=1) 기준이다.
패드 모델이나 드라이버에 따라 다를 수 있으므로 반드시 가짜 로봇에서 방향과 LB 해제를 먼저 확인한다.

## 2. 가짜 로봇에서 먼저 확인

기존 로봇 실행이 있다면 동작 완료 후 팔 컨트롤러를 inactive로 바꾸고 그 실행 터미널에서 Ctrl+C로 종료한다.
동일 도메인에서 실물과 가짜 드라이버를 동시에 실행하지 않는다.

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_xbox.sh use_fake_hardware:=true
```

하드웨어·MoveIt·테이블 모델·RViz·Servo·joy_node가 함께 실행된다.
`Servo ready`가 나오면 LB에서 손을 한 번 뗀 뒤 아래 조작을 확인한다.

| 입력 | 동작 (로봇 베이스 좌표 기준) |
|---|---|
| **LB 누른 상태** | 스틱 이동 명령 허용 |
| 왼쪽 스틱 위/아래 | 앞/뒤 (+X/-X) |
| 왼쪽 스틱 왼쪽/오른쪽 | 왼쪽/오른쪽 (+Y/-Y) |
| 오른쪽 스틱 위/아래 | 위/아래 (+Z/-Z) |
| 오른쪽 스틱 좌/우 | Z축 회전 |
| **LB + RB** + 왼쪽 스틱 좌/우 | X축 회전 |
| **LB + RB** + 왼쪽 스틱 위/아래 | Y축 회전 |
| LB 해제 | 이동 명령 0 |
| **B** | 이동 입력 차단. LB를 놓았다가 다시 눌러 재개 |
| 입력이 0.15초 이상 끊김 | 이동 명령 0, LB를 놓았다가 다시 눌러 재개 |

LB + RB 모드에서는 오른쪽 스틱 상하는 사용하지 않는다.
최대 직선 속도 0.3 m/s, 회전 속도 1.5 rad/s이며 입력 크기에 비례한다.
그리퍼 버튼 조작은 아직 추가하지 않았다.
B/LB는 소프트웨어 입력 제어이며 장비의 비상정지 기능을 대체하지 않는다.

## 3. 실물 실행

가짜 실행을 Ctrl+C로 종료한다.
기존 QUICK_START_KO.md처럼 rtprio 99, 유선 연결, Desk 관절 잠금 해제 및 Activate FCI를 준비한다.

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_xbox.sh use_fake_hardware:=false
```

실제 자세와 RViz 표시가 같은지, 테이블 모델이 실제 설치와 맞는지 확인한다.
새 터미널에서:

```bash
source ~/ros2_ws/install/setup.bash
```

```bash
ros2 control set_controller_state fr3_arm_controller active
```

활성화하면 제어 토크가 걸릴 수 있다. LB를 놓은 상태에서 준비하고, LB를 누른 채 스틱을 조금 기울려 시험한다.
**Plan/Execute 버튼 없이 스틱 입력 동안 연속 이동한다.**
이 구성은 RViz Execute를 비활성화하며 팔 궤적 입력은 Servo가 담당한다.
처음에는 가짜 로봇에서 입력 방향을 확인한 뒤 실물에서 작은 이동으로 시작한다.

종료: LB 해제 → 아래 명령 → 실행 터미널 Ctrl+C.

```bash
ros2 control set_controller_state fr3_arm_controller inactive
```

## 설정 및 진단

- 입력 노드: `src/fr3_skills/fr3_skills/xbox_teleop.py`
- Servo 속도·프레임·충돌 검사: `src/franka_ros2/franka_fr3_moveit_config/config/fr3_servo.yaml`
- 입력 토픽: `/fr3/joy` (다른 로봇의 `/joy`와 분리)
- 속도 명령: `/servo_node/delta_twist_cmds`
- Servo 출력: `/fr3_arm_controller/joint_trajectory`
- 상태: `/servo_node/status`
- 테이블 모델이 등록될 때까지 Servo 시작을 기다린다.
- Servo 충돌 검사와 특이점·관절 한계 감속/정지를 활성화했다. 등록되지 않은 장애물은 감지하지 않는다.
- LB를 누른 채 시작하거나 입력이 끊겼다가 재연결되면 LB를 놓았다가 다시 눌러야 한다.
- Xbox 실행 스크립트에만 기본 CycloneDDS participant index 상한 100을 적용한다. 기존 custom CYCLONEDDS_URI가 있으면 유지한다.

입력 확인:

```bash
ros2 topic echo /fr3/joy
```

```bash
ros2 topic echo /servo_node/status
```

2026-10-15 검증: 분리된 도메인 78의 가짜 FR3에서 모사 Xbox 입력에 따른 관절 이동,
LB 해제/B/입력 timeout 시 0 명령 확인. 최종 Servo 상태 0.
실제 Xbox 패드가 아직 인식되지 않아 실제 축·버튼 매핑과 실물 Servo 주행은 미검증이다.
