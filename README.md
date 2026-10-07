# franka_ros2_ws: FR3 실물 제어 + Bin Picking

Franka Research 3 실물을 ROS2 Humble + MoveIt2로 제어하고, 이후 카메라 기반 Bin Picking으로 확장하는 워크스페이스.

## 이 저장소에 있는 것

| 경로 | 내용 |
|---|---|
| src/fr3_skills/ | 동작 API (move_home, 이후 move_to_pose, gripper, pick/place) |
| scripts/ | 시험용 스크립트 |
| fr3.repos | 원본 패키지(libfranka, franka_ros2, ...) 버전 목록 |
| migration/ | franka_ros2 v2.0.2 수정 패치 + 새 컴퓨터 설치 가이드 |
| CLAUDE_HANDOFF_KO.md | 진행 기록 (작업 재개 시 가장 먼저 읽기) |

원본 패키지는 저장소에 포함하지 않는다.

## 새 컴퓨터에서 받기

```bash
git clone https://github.com/yezin293/franka_ros2_ws.git ~/franka_ros2_ws
```

```bash
cd ~/franka_ros2_ws
```

```bash
vcs import --recursive src < fr3.repos
```

```bash
git -C src/franka_ros2 apply ../../migration/franka_ros2_local_changes.patch
```

이후 의존성 설치, 빌드, rtprio, 네트워크 설정은 migration/MIGRATION_KO.md 4~7단계, 두 컴퓨터를 오가는 방법(git pull → 작업 → git push)은 9단계를 따른다.
