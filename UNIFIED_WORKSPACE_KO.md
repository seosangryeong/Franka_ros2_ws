# 단일 ROS 2 워크스페이스 (2026-10-15)

두 프로젝트의 공통 워크스페이스는 `/home/nuc/ros2_ws`다.
`franka_ros2_ws`와 `flanka_robo_ws` 내부에서 따로 colcon build/source하지 않는다.
모든 새 빌드 결과는 `~/ros2_ws/build`, `install`, `log`에 생성된다.

## 소스와 호환 버전

- `src/franka_ros2_ws/src`: franka_ros2 2.0.2, libfranka 0.15.0,
  franka_description 1.0.1, fr3_skills. 이전 실물 제어 수정 사항 유지.
- `src/flanka_robo_ws/src/dual_franka_description`: 양팔 FER 시뮬레이션 모델.
- ROS 2 Humble / Ubuntu 22.04, MoveIt 및 ros2_control 사용.
- Pinocchio 4.0.0과 libfranka 0.15.0의 빌드 성공 및 fake 경로계획/실행 확인.
  실물 FCI 호환성과 제어 성능은 로봇 전원을 켠 뒤 별도로 확인해야 한다.
- 다른 프로젝트 소스는 수정하지 않았다. 상위 src/libfranka(0.20.4)와
  src/olvx_descriptions_module은 보존하고, 루트 colcon_defaults.yaml의 검색 경로에서 제외했다.
- colcon_defaults.yaml은 현재 src 하위 프로젝트 목록을 명시한다.
  새 프로젝트를 추가하면 이 파일의 base-paths 목록도 갱신한다.
- Gazebo 전용 패키지, integration_launch_testing, 선택적 franka_ros2 메타패키지는
  기본 검색에서 제외한다. 실물 제어 및 Isaac 모델에는 필요하지 않다.
- flanka_robo_ws/teraffe_urdf는 ROS 1 참고 자산이라 COLCON_IGNORE로 빌드에서 제외한다.

## 보관한 이전 빌드

각 프로젝트의 복사된 build/install/log는 각 프로젝트 `.previous_pc/`에 있다.
상위 워크스페이스의 교체된 Franka build/install 패키지는
`~/ros2_ws/.franka_migration_backup/20261015_142333/`에 보관했다.
다른 패키지의 build/install 폴더는 유지했다.

## 다시 빌드

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/build_franka.sh
```

이 명령은 상위 ~/ros2_ws에서 관련 12개 패키지만 빌드한다.
일반적인 전체 빌드도 ~/ros2_ws에서 실행하며 기존 다른 프로젝트의 전체 빌드 성공까지 검증한 것은 아니다.

## 가짜 로봇 + RViz (실물 전원 불필요)

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_franka.sh use_fake_hardware:=true execute:=true load_table:=true
```

기본은 Franka Hand 포함이다. 가짜 Hand는 상태만 발행하므로 실제 그리퍼 동작 액션은 제공하지 않는다.
RViz MotionPlanning의 Planning Group은 fr3_arm, 속도/가속도 배율은 0.1.
목표 자세 조정 → Plan → Execute로 가짜 팔 이동을 확인한다.
기존 터미널에서 실행 중인 bringup이 있다면 중복 실행하지 말고 먼저 Ctrl+C로 종료한다.

## 실물 준비: 재부팅과 네트워크

계정 nuc의 rtprio 설정은 사용자가 아래 스크립트를 sudo로 실행했다.

```bash
sudo bash ~/ros2_ws/src/franka_ros2_ws/scripts/setup_rtprio.sh
```

현재 세션에는 적용되지 않는다. 작업 저장 후 PC를 재부팅하고 새 터미널에서 확인한다.

```bash
ulimit -r
```

99가 필요하다. 계정 nuc 전용 PAM 파일 및 user@1000.service 드롭인만 설정한다.
이는 PREEMPT_RT 커널 설치와 별개다. 현재 일반 커널의 실물 제어 안정성은 미검증이다.
공식 실시간 커널 지침: https://frankarobotics.github.io/docs/doc/libfranka/docs/real_time_kernel.html

로봇 전원 인가 후 PC 유선 LAN이 Control Box C2에 직결됐는지 확인한다.
연결된 유선 인터페이스가 하나면 아래 스크립트가 자동 선택한다.
둘 이상이면 로봇에 연결한 인터페이스 이름을 인자로 지정한다.

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/setup_network.sh
```

franka-direct 프로필에 PC 172.16.0.10/24를 설정한다. Wi-Fi 기본 경로는 변경하지 않는다.
기록된 이 PC 유선 장치는 enp131s0, enx00e04c680052다. 조사 당시 두 장치 carrier는 꺼져 있었다.
Desk: https://172.16.0.2/desk/ 에서 현재 오류, 장착 Hand, FCI 상태를 확인한다.
비밀번호와 물리적 잠금 해제 절차는 자동화하지 않는다.

## 실물 상태 + MoveIt 계획만 확인

가짜 실행을 종료한 뒤 실행한다. Hand가 없다면 load_gripper:=false를 추가한다.

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_franka.sh use_fake_hardware:=false execute:=false
```

실제 관절 상태가 RViz에 표시되는지 확인한다. 팔 모션 컨트롤러는 inactive로 로드된다.
2026-10-15 후속 확인: 실물 하드웨어 연결과 상태 broadcaster active 확인. FCI 비활성 시 연결 거부 오류가 있었으므로 Desk에서 Activate FCI 후 사용한다.

## RViz에서 실물 실행

실제 Hand, 테이블 및 주변 장애물 모델이 설치 환경과 일치하는지 먼저 확인한다.
저장된 table_floor는 이전 설치 환경 기준이다. 필요하면
src/fr3_skills/fr3_skills/motion.py의 TABLE_* 값을 실제 치수/좌표에 맞춘다.
load_table:=true는 그 박스를 추가하는 옵션이며 다른 장애물을 자동 인식하지 않는다.

계획 전용 실행을 종료하고 아래로 다시 시작한다. 이 명령만으로 팔 모션 컨트롤러가 활성화되지는 않는다.

```bash
bash ~/ros2_ws/src/franka_ros2_ws/scripts/start_franka.sh use_fake_hardware:=false execute:=true load_table:=true
```

다른 터미널에서 공통 워크스페이스를 불러온다.

```bash
source ~/ros2_ws/install/setup.bash
ros2 control list_controllers
```

실물과 RViz 현재 자세가 일치하는지 확인하고, 현재 자세 근처의 작은 목표를 Plan해 경로를 검토한다.
실제로 움직일 준비가 됐을 때만 활성화한다(제어 토크가 시작될 수 있다).

```bash
ros2 control set_controller_state fr3_arm_controller active
```

RViz의 Execute로 검토한 경로를 실행하고 끝나면 비활성화한다.

```bash
ros2 control set_controller_state fr3_arm_controller inactive
```

팔 목표점만 확인하지 말고 손목·팔꿈치를 포함한 전체 경로를 확인한다.
이전 기록에 테이블 프로파일과 팔의 접촉 이력이 있으며, 저장된 테이블 박스는 전체 주변 구조물 모델이 아니다.

## 검증 결과

- 관련 12개 패키지 빌드 성공, 단일 소스 검색에서 중복 패키지 없음.
- franka_hardware가 통합 install/libfranka의 libfranka.so.0.15를 링크하는 것 확인.
- RViz OpenGL 4.6 로드, fr3_arm MoveGroup 연결 성공.
- 도메인 77 가짜 하드웨어에서 MoveIt 계획 → ExecuteTrajectory → 관절 상태 반영 성공.
  관절1 목표 +0.03 rad, 최종 목표 오차 0.000564 rad (플래너 허용 오차 내).
  일반 도메인의 RViz + table_floor 등록 상태에서도 재시험 성공(오차 0.000619 rad).
  scripts/verify_fake_motion.py는 GenericSystem 여부를 먼저 확인하며 실물에서는 실행을 거부한다.
- table_floor 등록 성공, 양팔 xacro 생성 및 check_urdf 검사 성공.
- Isaac Sim USD 재생성/실행은 이번 ROS 실물 제어 범위에서 검증하지 않았다.
- 2026-10-15 후속 확인: rtprio 99, 유선 연결 및 실물 드라이버 연결 확인. 사용자가 팔 컨트롤러 active 후 RViz Execute로 실물 이동 성공을 확인했다. 빠른 사용법은 QUICK_START_KO.md 참고.
