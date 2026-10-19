# FR3 실물 제어 — 빠른 사용법

워크스페이스: `~/ros2_ws` · ROS 2 Humble · 로봇 IP: `172.16.0.2`

2026-10-15: 아래 구성에서 실물 이동 성공 확인.

## 1. 로봇과 Desk 준비

1. 로봇 전원을 켠다.
2. PC의 유선 LAN을 Control Box의 **C2 포트**에 연결한다.
3. 브라우저에서 **https://172.16.0.2/desk/** 접속 후 로그인한다.
4. Desk에서 오류 여부를 확인하고 관절 잠금을 해제한다.
5. Desk 상단 **System → Activate FCI**를 누르고 확인한다.

FCI는 로봇/Desk 재시작 후 활성 상태를 다시 확인한다.

## 2. 터미널 1 — 연결 및 RViz 실행

실시간 권한 확인:

```bash
ulimit -r
```

**99**가 나와야 한다. 0이면 PC 재부팅 후 새 터미널에서 다시 확인한다.

유선 설정 및 연결 확인:

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/setup_network.sh
```

마지막에 `172.16.0.2`로 ping이 성공해야 한다.

**실물 드라이버 + MoveIt + RViz**를 함께 실행한다:

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_franka.sh use_fake_hardware:=false execute:=true load_table:=true
```

이 터미널은 계속 켜둔다. 중복 실행하지 않는다.
Franka Hand 장착 기준이며, 테이블 모델은 기존 설치 배치 기준이다.

## 3. RViz — 목표와 경로 지정

1. 실제 로봇과 RViz의 **현재 자세**가 같은지 확인한다.
2. MotionPlanning의 **Planning Group = fr3_arm**으로 선택한다.
3. 속도·가속도 배율을 **0.1**로 둔다.
4. 엔드이펙터 화살표·회전 링으로 가까운 목표를 정한다.
5. **Plan**을 누르고 팔 전체 경로와 주변 장애물을 확인한다.

화살표는 목표를 지정한다. 실물 이동은 Execute를 눌렀을 때 시작한다.
테이블이나 주변 배치가 달라졌다면 충돌 모델을 먼저 맞춘다.

## 4. 터미널 2 — 움직이기 직전 활성화

```bash
source ~/ros2_ws/install/setup.bash
```

```bash
ros2 control set_controller_state fr3_arm_controller active
```

**활성화하면 실물에 제어 토크가 걸릴 수 있다.**
성공하면 RViz에서 **Execute**를 눌러 계획한 경로로 실물을 움직인다.

동작이 끝나면 비활성화한다:

```bash
ros2 control set_controller_state fr3_arm_controller inactive
```

다음 동작도 목표 지정 → Plan → 컨트롤러 active → Execute → inactive 순서로 진행한다.

## 5. 실행 종료

팔 동작 완료 → 컨트롤러 inactive → 터미널 1에서 **Ctrl+C**.
로봇 전원 종료는 Desk/장비의 정상 종료 절차를 따른다.

## 안 움직일 때

| 증상 | 확인할 것 |
|---|---|
| `Connection to FCI refused` | Desk의 **Activate FCI** |
| 화면만 움직임 | 실행 인자가 `use_fake_hardware:=false`인지 확인 |
| 실물 연결은 됐지만 Execute가 안 됨 | `fr3_arm_controller`가 **active**인지 확인 |
| 드라이버 재실행 후 안 움직임 | 팔 컨트롤러는 다시 inactive로 시작하므로 움직이기 직전에 활성화 |
| `ulimit -r`이 0 | PC 재부팅 후 새 터미널에서 확인 |
| ping 실패 | 로봇 전원·C2 케이블·유선 설정 확인 |

컨트롤러 상태 조회(터미널 2):

```bash
ros2 control list_controllers
```

## 필요할 때만 다시 빌드

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/build_franka.sh
```

평소 실행할 때는 다시 빌드할 필요 없다. 상세 구성과 백업 위치는 `UNIFIED_WORKSPACE_KO.md` 참고.

Xbox 조작은 [XBOX_TELEOP_KO.md](XBOX_TELEOP_KO.md) 참고.
