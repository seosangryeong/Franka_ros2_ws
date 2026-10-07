# Claude 인수인계 — Franka 실물 제어

최종 기록: 2026-10-02 (한국 시간). 이 문서를 먼저 읽고 PROJECT_CONTEXT.md 및 FRANKA_PROJECT_PLAN_KO.md를 참고한다. 과거 기록과 충돌하면 최신 날짜의 확인된 결과를 우선한다. 저장 시점의 실시간 로봇 상태는 조회하지 않았다.

## 사용자 목표와 작업 방식

Ubuntu 22.04 / ROS2 Humble / VS Code / 실물 Franka Research 3. 워크스페이스는 /home/research_108_01/franka_ros2_ws. 인수인계 없이 시작한 사용자라 설명은 한국어로 쉽고 짧게 한다. 사용자는 Piper처럼 목표 pose → MoveIt IK/경로계획 → 실제 이동을 원한다.

최종 구조: 사용자 코드 → MoveIt2 → ros2_control의 trajectory controller → franka_ros2 하드웨어 → libfranka/FCI → 실물. Desk는 준비·상태·FCI 활성화에 사용하며 Desk 자체에서도 작업 작성이 가능하다. launch에 따라 하드웨어와 MoveIt이 통합 실행될 수 있으므로 반드시 세 터미널로 고정할 필요는 없다.

우선순위: 환경/통신/상태 → MoveIt 실물 연결 → 현재 자세 근처 작은 이동 → HOME/READY/Pose A/B → 그리퍼 → 재사용 API → Bin Picking → OBSBOT RGB 카메라/좌표변환. 카메라와 인식 구현은 아직 시작하지 않는다.

향후 API 희망: move_to_pose(x,y,z,qx,qy,qz,qw), open_gripper(), close_gripper(), move_home(), move_ready(), pick(object_pose), place(place_pose). 아직 구현하지 않았고 HOME/READY도 정의되지 않았다. RGB의 픽셀만으로 깊이는 정해지지 않아 향후 평면/높이/형상 조건과 보정이 필요하다. 처음부터 반드시 직접 학습해야 하는 것은 아니다.

## 가장 중요한 현재 상태

1. 기존 소프트웨어 조사 완료, Desk 및 FCI를 통한 실물 상태 수신 성공.
2. rtprio 적용 및 FIFO priority 98 성공. broadcaster 100Hz로 줄인 짧은 시험에서 잠금 오류 재발 없음. 장시간 안정성은 미검증.
3. RViz 및 MoveGroup fr3_arm 연결, OMPL RRTConnect Plan 성공(0.0138672초).
4. 사용자가 Execute를 눌렀지만 실물은 움직이지 않았다고 보고. **실물 이동 성공은 없다.** 계획 전용 launch에 allow_trajectory_execution=False가 남아 있고 실행 controller 연결도 준비되지 않았다. True 한 줄만 바꿔 완료된다고 처리하지 않는다.
5. 그 후 RViz GLX/OpenGL 오류로 화면도 안 열림. RViz 단독 및 소프트웨어 렌더링도 실패. **지금은 그래픽 복구가 첫 진단 과제다.**
6. 노트북 재부팅을 안내했지만 수행/복구 확인은 아직 없다. 실제 로봇·ROS 현재 상태는 새로 확인해야 한다.

## 기존 환경 및 네트워크

- Ubuntu 22.04.5, 기존 커널 6.8.0-138-generic. 변경 없음.
- franka_ros2 2.0.2, libfranka 0.15.0, franka_description 1.0.1.
- Control 시스템 5.8.1, Arm3R connected 및 Status/Safety ok 화면 확인 이력. FCI feature 1.0.0은 시스템 버전과 별개. 공식 호환표는 PROJECT_CONTEXT.md 참고.
- src/franka_ros2, src/libfranka, src/franka_description, src/olvx_descriptions_module(olv_module_descriptions 0.0.1). 전체 15개 패키지, build/install/log 존재, 마지막 조사 빌드 2026-09-11 15:39 성공. MoveIt2 및 joint_trajectory_controller 설치 확인.
- 노트북 enp129s0: 172.16.0.10/24.
- Control Box C2 Shop Floor: 172.16.0.2/24. Desk https://172.16.0.2/desk/ 및 FCI 연결 대상.
- 베이스 X5 Robot network: 192.168.0.1/24. 현재 노트북 C2 직결 유지.
- NetworkManager franka-direct: manual IPv4, gateway/DNS 없음, never-default yes, autoconnect yes priority100, IPv6 disabled, dad-timeout3000. 기존 Wired connection1 보존. Wi-Fi 기본 경로 보존.
- admin 및 safety 계정 존재. 비밀번호는 문서에 저장하지 않음.
- 과거 Non-recoverable safety error와 Desk reboot 후 흰색 점멸/접속 불능 기록. 사용자가 Control Box 전원 재투입 후 복구. 원인 미확정, 일반 재부팅 방법으로 권장하지 않는다. Factory Reset/Pack Pose 실행 안 함.

## 변경 파일: 오늘 재확인한 Git 상태

src/franka_ros2에서 수정된 네 파일:

| 파일 | 변경 및 의미 |
|---|---|
| franka_bringup/config/controllers.yaml | 상세 상태 broadcaster update_rate:100 추가. manager1000 유지, lock_try_count5/sleep5, lock_log_error:true, lock_update_success:false 유지. 오류 숨김 아님. |
| franka_fr3_moveit_config/launch/move_group.launch.py | 인자 선언, kinematics 계층, OMPL 구성, panda_arm→fr3_arm 매핑, joint_states→franka/joint_states remap, RViz 옵션. allow_trajectory_execution=False. 자체 hardware/controller/gripper launch 없음. |
| franka_fr3_moveit_config/rviz/moveit.rviz | Planning Group fr3_arm, MotionPlanning 활성화. |
| franka_semantic_components/CMakeLists.txt | 사용자의 기존 controller_interface 의존성 변경. 보존할 것. |

설치 launch/config는 소스 symlink여서 위 수정 당시 재빌드 불필요. Python 문법/show-args/Xacro/SRDF 그룹 검증 완료 이력. Git reset/패키지 교체로 일괄 되돌리지 말 것. commit/push 안 함.

시스템 파일 /etc/security/limits.d/99-franka-research.conf는 사용자가 직접 작성:

```text
research_108_01 soft rtprio 99
research_108_01 hard rtprio 99
```

재로그인 후 ulimit -r99, controller_manager FIFO98 성공. 99는 허용 상한이며 그 자체가 CPU를 사용하는 설정은 아니다.

**기존 별도 파일 주의:** franka_fr3_moveit_config/config/fr3_ros_controllers.yaml에는 원래 lock_log_error:false / lock_update_success:true가 있다. 이번 기본 bringup 진단에서 사용하는 controllers.yaml과 다르다. 통합 launch로 전환하면서 오류가 안 보이는 것만으로 해결 판정하면 안 된다.

## 검증한 launch와 실행 연결의 빈 부분

각 터미널에서 먼저:

```bash
cd ~/franka_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

터미널1 — 실물 상태 bringup (중복 실행 금지):

```bash
ros2 launch franka_bringup franka.launch.py robot_ip:=172.16.0.2 arm_id:=fr3 use_fake_hardware:=false load_gripper:=false
```

joint_state_broadcaster 및 franka_robot_state_broadcaster active 확인. 팔 동작용 fr3_arm_controller는 이 구성으로 활성화하지 않았다.

터미널2 — 계획 전용 MoveIt/RViz:

```bash
ros2 launch franka_fr3_moveit_config move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false
```

RViz 없는 분리 진단 인자 use_rviz:=false 지원. 실행 안내는 했지만 해당 방식 정상 유지 결과는 아직 없다.

기존 moveit.launch.py는 하드웨어/controller manager까지 포함하는 통합 구성이다. **기본 bringup과 동시에 켜지 말 것.** 기존 fr3_ros_controllers.yaml의 fr3_arm_controller는 effort JointTrajectoryController, position/velocity 상태, joint1~7 및 PID gains 정의. 이를 현재 manager에 정확히 어떻게 로드/연결할지 아직 구현하지 않았다. MoveIt controller mapping(fr3_controllers.yaml), 실제 FollowJointTrajectory 서버, 관리 namespace와 인터페이스를 함께 검증해야 한다.

기존 gripper 참조 fr3_gripper와 실제 노드 franka_gripper 불일치 가능성 미해결. load_gripper=false로 계획했고 실물 Hand가 모델에 빠져 있다. 그리퍼 homing/open/close 모두 미시험.

## 상태 발행 잠금 오류 경과

원래 로그: Failed to lock the realtime publisher after 5 attempts; controller update ERROR 반복. 약1kHz 관절/상태 수신은 되기도 했고 한번 topic hz에서 미발행 경고도 있었다. topic 존재만으로 정상 발행을 판단하지 않는다.

broadcaster 소스 trylock 재시도/실패시 해당 갱신 누락 동작 조사. 설치된 ros2_control의 개별 controller update_rate 지원 확인 후 상세 broadcaster에만100Hz 설정. 사용자 param100 및 약99.97~100.02Hz, 9~11ms 간격 확인. 후속 제공 로그에 lock ERROR 없음. 제어 루프1000Hz 변경 안 함. 근본 원인 확정/장시간 실기 안정성 인증은 아니다. CLI message lost 한 건을 FCI 패킷 손실로 단정하지 않는다.

실물 /franka/joint_states 이름 순서가 joint1,3,6,7,2,4,5였음. **항상 name으로 position 매핑**한다. 과거 측정 joint1~7 rad:
[-0.195533899, 0.088273913, 0.114479593, -2.235051960, 0.072861632, 2.281744737, 0.753980274]. 오래된 참고값이며 현재 목표/HOME으로 사용하지 말 것.

## 오늘 그래픽/종료 오류와 증거

RViz: Failed to create an OpenGL context. BadValue / Unable to create a suitable GLXContext, OgreGLXContext.cpp line60. 저장된 MoveIt RViz 설정 없이 rviz2 단독도 같은 오류.

사용자가 아래 실행도 실패했다고 보고:

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch franka_fr3_moveit_config move_group.launch.py robot_ip:=172.16.0.2 load_gripper:=false
```

로그 경로:
- ~/.ros/log/2026-10-02-14-35-08-334959-2204-193370/launch.log
- ~/.ros/log/move_group_193396_1790919308544.log
- ~/.codex/attachments/5b0f815b-00de-42e5-b69c-be526eaf412e/Pasted text.txt

launch.log에서 move_group 초기화 완료 → Ctrl+C(SIGINT) → exit -11 순서가 확인됐다. 종료 중 충돌 가능성이 있으며 시작부터 실패했다고 단정하지 않는다. RViz 종료시 SIGTERM10초 후 SIGKILL / exit-9 기록도 있다. 종료되지 않아 강제 정리된 기록이며 새로운 원인 증거는 아니다.

move_group 로그에는 No controller_names specified / Returned 0 controllers도 있다. 실행 연결 누락의 추가 근거. /recognize_objects 없음 및 Octomap sensor plugin 없음은 인식 미구성 상태에서 관측됐고 과거 Plan 성공을 막지 않았다.

사용자가 Ctrl+Z를 여러 번 사용: 이는 종료가 아니라 Stopped 상태다. 같은 터미널 jobs -l 확인 → 해당 번호 fg %N → Ctrl+C 안내. 무조건 특정 job 번호를 재사용하지 말 것. 수행 완료 미확인.

도구 환경 DISPLAY=:0, SESSION=x11. sandbox ps에 ROS 프로세스 없음은 호스트 상태를 보장하지 않는다. sandbox ROS socket PermissionError는 도구 권한 제한이며 사용자 로봇 고장 아님. 권한 확대 조회에서는 그 시점 controller_manager 응답 없음 / move_group Node not found.

glxinfo -B 및 사용자 그래픽 변수 조회를 요청했지만 출력 못 받음. glxinfo 도구도 설치 여부 미확정, 진단 위해 무조건 설치하지 않는다. 소프트웨어 렌더링 실패만으로 GPU 고장을 단정하지 말 것.

사용자 노트북 재부팅 의향: 저장 → MoveIt/RViz와 bringup Ctrl+C 종료 → 정지 확인 → 노트북 정상 재시작 → ROS bringup 전에 source /opt/ros/humble/setup.bash 및 rviz2 단독 시험 안내. 완료/결과 미확인. 이 그래픽 문제 때문에 Control Box 전원 재투입은 제안하지 않았다.

## 현장 사진과 안전 범위

테이블600×600×800mm, 3030 프로파일, 상판 없음(추후 설치). 베이스는 한 변 중앙 부근에 직접 볼트/너트/스프링 와셔로 고정, 별도 플레이트 없음(사용자 설명). 내부/외곽 레일, 아래 상자, 케이블, 주변 가구가 사진에 보인다. 실제 Hand 장착. 사진에서 정확한 TF/오프셋/고정 강성은 알 수 없다.

사용자는 상세 CAD보다 작은 실물 제어 진행을 원하고, 아래 프로파일 접촉만 피하면 된다고 설명했다. 실행 구성 준비와 작은 실물 시험 진행 의사는 반복 확인됐다. 같은 승인 질문을 반복하지 말고 가능한 준비를 진행한다. 다만 TCP z>=0 제한은 팔 전체 충돌 회피가 아니다. 비상정지가 충돌 방지를 보장한다고 설명하지 않는다. 예제 Cartesian controller가 자동으로 큰 궤적을 만드는지 확인 없이 실행하지 않는다.

첫 시험 후보로0.01rad 단일 관절 변경을 언급했으나 관절/방향/속도/목표는 미선정. **실제 명령으로 확정된 숫자가 아니다.** 현재 상태와 전체 경로 및 환경을 확인해 결정한다.

## Claude가 다음에 할 순서

1. 재부팅 여부, 남은 일시정지 프로세스 및 RViz 단독 결과 확인. glxinfo가 있으면 glxinfo -B, DISPLAY/session 및 관련 렌더링 환경변수 조회. 원인 없이 드라이버/커널 변경 금지.
2. 현재 Desk FCI/관절/오류 및 실제 ROS node/controller/joint state 확인. 중복 hardware launch 금지. 이전 성공값을 현재로 간주하지 않는다.
3. 기존 파일을 활용해 실제 trajectory controller + MoveIt mapping/action 연결을 구체적으로 준비. 아직 실행을 허용하지 않은 구성임을 사용자에게 명확히 설명. 현재 경로를 그대로 무작정 실행하지 않는다.
4. 실물 Hand/프로파일 충돌 범위를 반영하고 현재 관절과 계획 시작 상태 일치 확인. 필요한 최소 정보로 진행하며 완전한 CAD를 필수로 고집하지 않는다.
5. 무엇이 얼마나 움직이는지/명령을 먼저 보여주고 현재 근처 작은 계획 검토 → 실행 → 실제 상태/오류 검증.
6. 그 후 검증된 HOME/READY, 그리퍼, API, Bin Picking 순으로 확장.

## 환경 보존 및 인수인계 주의

커널 설치/변경 금지. 네트워크 드라이버/ROS/libfranka/franka_ros2 버전 변경과 패키지 재설치는 필요 근거 없이 하지 않는다. 기존 workspace 삭제·재생성 금지. 작은 수정만 한다. 물리 이동 전 설명/명령/상태 확인 원칙 유지. 사용자 질문에는 짧게 먼저 답하고 도구 작업 중 진행 상황을 알린다.

Codex 응답이2~3회 질문 뒤 멈추고 재접속하면 복구된다는 사용자 보고, 확장 재설치 후에도 반복. VS Code 버전/로그 미확보. rtprio99나 오래된 VS Code가 원인이라고 확정하지 않았다. VS Code/확장 삭제나 시스템 업데이트 수행 안 함.

이번 인수인계에서는 문서만 저장. 새 제어 패키지/모션 스크립트 생성, controller 활성화, 로봇·그리퍼 이동, Git commit/push 수행 안 함. 로봇 정상 종료도 에이전트가 수행하지 않았다.

## 2026-10-02 15:20 추가 (Claude)

- 노트북 재부팅 확인(부팅 15:07). 남은 ROS/일시정지 프로세스 없음. 172.16.0.2 ping 정상.
- GPU: RTX 5090 Laptop, NVIDIA 580.178.04, prime on-demand. **rviz2 단독 정상(OpenGL 4.6, GLX 오류 없음)** → 그래픽 문제는 재부팅으로 해소. 드라이버 변경 없음. glxinfo 미설치(설치 안 함).
- 실행 연결 준비(실물 미실행):
  - 새 파일 franka_fr3_moveit_config/config/fr3_arm_controller_real.yaml: effort JTC, 기존 PID 게인 동일, constraints(trajectory 0.05rad, goal 0.01rad, goal_time 0.5s) 추가. controllers.yaml은 변경 안 함.
  - move_group.launch.py에 `execute` 인자 추가(기본 false → 기존 계획 전용 동작 유지). true일 때 fr3_arm_controller 매핑(그리퍼 제외), moveit_manage_controllers=false, allowed_start_tolerance 0.01.
  - franka_fr3_moveit_config만 symlink 재빌드.
- fake hardware(ROS_DOMAIN_ID=77, localhost)로 검증: spawner -p ... --inactive 로드 OK, MoveIt "Added FollowJointTrajectory controller", /fr3_arm_controller/follow_joint_trajectory 확인, activate/deactivate 전환 OK. 궤적 실행은 fake에서도 안 함. 테스트 프로세스 정리 완료.
- 실물 이동 성공 여전히 없음. 실물에서 effort JTC 활성화 시 동작은 미검증.

## 2026-10-02 오후 실물 결과 (위 "실물 이동 성공 없음"을 대체)

- spawner `--inactive -p fr3_arm_controller_real.yaml` → activate → RViz Plan/Execute로 **실물 이동 성공**(여러 번 `Goal reached, success!`). 관절2 약0.21rad 등.
- **미해결: ros2_control_node exit -6(abort) 2회**(15:40:28, 15:51:09). 둘 다 Execute 성공 후 fr3_arm_controller를 active로 둔 채 대기 중(44초/86초 후). 원인 메시지는 터미널1 화면에만 출력되어 미확보. 후보: libfranka communication_constraints_violation(일반 커널) 또는 reflex. 미확정.
- bringup이 죽으면 새 controller_manager에는 fr3_arm_controller가 없으므로 spawner부터 다시 필요(사용자 혼란 원인).
- 운영 규칙: 움직이기 직전 activate, 끝나면 즉시 deactivate. bringup은 `2>&1 | tee ~/bringup_$(date +%H%M).log`로 실행해 원인 확보.
- 배경: snapd-desktop-integration 2초 주기 재시작 루프(880회+) 관측. 손대지 않음.
- 사용자 선호: 명령은 코드블록 하나당 하나 + 한 줄 설명(노션 정리용). 설명은 원리 위주로, 직접 실행하며 이해하고 싶어 함.

## 2026-10-07 (Claude)

- 새 패키지 src/fr3_skills (ament_python): motion.py의 Fr3Motion(현재 관절 이름 매핑, MoveGroup 계획, 계획 요약, 컨트롤러 active 확인 후 ExecuteTrajectory, scaling 상한 0.2), `ros2 run fr3_skills move_home [--execute] [--scaling]`. HOME = config/poses.yaml = SRDF ready. 실물 미검증.
- fake hardware(도메인77)로 계획/실행거부/scaling 거부 확인. 테스트 프로세스 정리.
- 합의한 구조: ①드라이버 ②fr3_skills ③perception/calibration ④bin_picking 상태머신. 카메라 전에 가짜 물체 좌표로 ④ 먼저.
- 사용자가 더 큰 노트북(ROS 기반)으로 실물 제어까지 이전 희망. 이전 묶음 ~/fr3_migration_20261007.tar.gz(28K) 생성: migration/MIGRATION_KO.md(단계별 가이드), franka_ros2_local_changes.patch(v2.0.2 깨끗한 checkout에 git apply --check 통과), fr3_skills, scripts, 문서 3개. 원본 패키지는 같은 태그로 재clone. 새 노트북 사양(Ubuntu/ROS 버전, 이더넷) 미확인.
- 이후 GitHub 비공개 저장소 https://github.com/yezin293/franka_ros2_ws 로 전환(사용자가 직접 push). 압축 묶음 대신 clone → vcs import --recursive src < fr3.repos → 패치 적용. 운영: git pull → 작업 → commit → push. 원본 패키지는 .gitignore, franka_ros2 수정 시 migration/ 패치 재생성 필요.
