# Command & Conquer: Red Alert 2 & Yuri's Revenge - Custom Mod Configuration

This repository / installation contains custom modifications and engine fixes for **Command & Conquer: Red Alert 2** and **Command & Conquer: Yuri's Revenge**.

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Prerequisites System Overhaul](#prerequisites-system-overhaul)
3. [Buildable Tech & Civilian Structures](#buildable-tech--civilian-structures)
4. [Bunkers & Base Defenses](#bunkers--base-defenses)
5. [Combat & Unit Fixes](#combat--unit-fixes)
6. [Engine Bugfixes & Infiltration Logic](#engine-bugfixes--infiltration-logic)
7. [Modified Files Reference](#modified-files-reference)
8. [Installation & Restoration](#installation--restoration)

---

## 🌟 Overview

The configuration modifies `rules.ini`, `rulesmd.ini`, `art.ini`, and `artmd.ini` to streamline base development, remove tech-tree bottlenecks, unlock civilian/tech buildings directly into the build queues, enhance defensive structures, and fix specific Westwood engine bugs.

---

## ⚡ Prerequisites System Overhaul

### 1. Buildings (Structures, Defenses & Superweapons)
All building prerequisites have been disabled across both RA2 and Yuri's Revenge.
- **Immediate Building Availability**: As soon as a Construction Yard is deployed, every building, defense, and superweapon is immediately available in the sidebar without requiring power plants, refineries, or prerequisite buildings.
- **Affected Structures**:
  - **Factories & Production**: Barracks (`GAPILE`, `NAHAND`, `YABRCK`), War Factories (`GAWEAP`, `NAWEAP`, `YAWEAP`), Naval Yards (`GAYARD`, `NAYARD`, `YAYARD`), Service Depots.
  - **Tech & Radar**: Battle Labs (`GATECH`, `NATECH`, `YATECH`), Radar Stations (`NARADR`, `GAAIRC`, `AMRADR`, `NAPSIS`), Ore Purifier, Robot Control Center, SpySat, Gap Generator, Industrial Plant, Nuclear Reactor, Cloning Vats.
  - **Superweapons**: Nuclear Missile Silo, Iron Curtain, Chronosphere, Weather Machine / Lightning Storm, Psychic Dominator, Genetic Mutator.
  - **Defenses**: Grand Cannon, Prism Tower, Tesla Coil, Gatling Cannon, Psychic Tower, Pillbox, Sentry Gun, SAM Site, Patriot Missile, Flak Cannon, Walls, and Gates.

### 2. Units (Infantry, Vehicles, Ships & Aircraft)
Unit prerequisites have been streamlined so they only require their primary production facility:
- **Infantry**: All infantry units (including Spy, Chrono Legionnaire, Boris, Yuri Prime, Tanya, Rocketeers, Snipers, Desolators) require only a `Barracks`. All Battle Lab, Radar, and mission-override restrictions were removed.
- **Ground Vehicles**: All vehicles (including Apocalypse Tank, Prism Tank, Mirage Tank, Battle Fortress, Kirov Airship, Magnetron, Master Mind, V3 Rocket, Demolition Truck, Robot Tank) require only a `War Factory`. No Battle Lab, Radar, or Ore Refinery is required.
- **Naval Units**: All naval units (including Aircraft Carrier, Dreadnought, Giant Squid, Boomer Sub, Aegis Cruiser, Dolphin) require only a `Naval Yard`.
- **Aircraft**: Aircraft (Harrier, Black Eagle) require only the `Airfield / Air Force Command`.

---

## 🏗️ Buildable Tech & Civilian Structures

Civilian tech buildings have been integrated into the sidebar construction menu for all factions:

| Building | Code | Cost | Build Tab | Special Ability / Benefit |
| :--- | :--- | :--- | :--- | :--- |
| **Tech Oil Derrick** | `[CAOILD]` | \$1000 | Buildings | Produces periodic income automatically (`NeedsEngineer=no`). |
| **Tech Airport** | `[CAAIRP]` | \$1000 | Buildings | Functions as a complete **Construction Yard** (`ConstructionYard=yes`, `Factory=BuildingType`) with radar and 4 docking pads, unlocking full base building upon capture, retaining 4 helipads for Harriers & Black Eagles, and granting the **Allied Paradrop** superweapon. |
| **Tech Civilian Hospital** | `[CAHOSP]` / `[CATHOSP]` | \$1000 | Buildings | Grants global passive infantry auto-healing. |
| **Tech Machine Shop** | `[CAMACH]` | \$1000 | Buildings | Grants global passive vehicle auto-repair. |
| **Tech Civilian Power Plant** | `[CAPOWR]` | \$1000 | Buildings | Generates +200 clean power; spy-infiltratable. |
| **Tech Secret Lab** | `[CASLAB]` | \$1000 | Buildings | Grants access to random secret tech units. |
| **Tech Outpost** | `[CAOUTP]` | \$1000 | Defenses | Armed defensive outpost with heavy firepower and vehicle repair pad. |

*Notes*:
- All tech buildings feature `Adjacent=100` for flexible base placement.
- Sidebar icons (cameos) and theater art dependencies (`DemandLoad=false`) have been configured in `art.ini` and `artmd.ini`.
- **Tech Airport Construction Yard & Air Wing Base**:
  - **Integrated Construction Yard**: Configured with `ConstructionYard=yes`, `Factory=BuildingType`, and `EligibileForAllyBuilding=yes`. Capturing a map Tech Airport immediately unlocks the **Buildings** and **Defenses** sidebar construction queues, serving as your primary base headquarters without needing an MCV.
  - **Built-in Radar Station**: Equipped with active radar (`Radar=yes`) and registered in `PrerequisiteRadar` under `[General]` so it powers the minimap and satisfies all radar tech prerequisites.
  - **4-Pad Airfield & Aircraft Servicing**: Features 4 dedicated runway docking pads (`NumberOfDocks=4`, `Helipad=yes`, `UnitReload=yes`, `Dock=...,CAAIRP`). Any Harriers (`[ORCA]`) or Black Eagles (`[BEAG]`) built from your newly placed Air Force Command can land, reload missiles, and repair to 100% health at the Tech Airport.
  - **Allied Paradrop**: Retains the recurring Allied Reinforcement Paradrop support power on a timer cooldown.

---

## 🛡️ Bunkers & Base Defenses

### 1. Concrete Bunker (`[CABUNK01]`)
- **Buildable for All Factions**: Placed on the Defenses/Combat sidebar tab.
- **Cost**: \$500 | **Health**: 2,000 HP | **Armor**: `steel`.
- **Capacity**: Holds **8 infantry** (`MaxNumberOccupants=8`, `CanOccupyFire=yes`).
- **Full Firing Coverage**: All 8 occupants fire outward simultaneously.
- **Visuals & Placement Fix**: Assigned `Image=NABNKR` and `Buildup=NABNKRMK` so the bunker plays its construction animation and renders visibly upon placement across all map theaters.

### 2. Soviet Battle Bunker (`[NABNKR]`)
- Upgraded health from 600 HP to **2,000 HP**.
- Expanded capacity from 5 to **8 infantry slots**.
- Activated muzzle flash positions 5, 6, and 7 in `artmd.ini` to support all 8 firing occupants.

---

## ⚔️ Combat & Unit Fixes

### 1. Navy SEAL (`[GHOST]`)
- Fully buildable at Tech Level 1 for all Allied, Soviet, and Yuri factions.
- Requires only a standard Barracks.

### 2. Tanya vs. Barrels (1-Shot Kills)
- Fixed Tanya's weapon (`DoublePistols` / `HollowPoint2` warhead) damage vs. barrels (`concrete` armor).
- Increased damage verse against concrete to **100%**, enabling single-shot barrel detonations.

### 3. Repair IFV (`[FV]`)
- **Friendly Wrench Cursor Restored**: Removed `AttackCursorOnFriendlies=yes` which had forced attack cursors instead of wrench repair cursors on friendly units.
- **Nighthawk Transport Repair**: Fixed `[Mechanical]` warhead verses for `special_2` armor so the IFV can repair Nighthawk Transports (`[SHAD]`).

### 4. Aegis Cruiser (`[AEGIS]`) All-Domain Targeting
- **Ground, Surface Naval, & Submarine Engagement**: Enabled full multi-role targeting by setting `LandTargeting=0` (land targets allowed) and `NavalTargeting=5` (all naval and underwater targets allowed with primary weapon).
- **Submarine Sonar & Tracking**: Equipped with active sonar sensors (`Sensors=yes`, `SensorsSight=10`) so it detects, tracks, and fires upon submerged submarines and underwater creatures.
- **Universal Weapon & Warhead Coverage**:
  - `[MedusaProjectile]`: Added `AG=yes`, `AN=yes`, `AS=yes`, `ASW=yes` while retaining `AA=yes`. Reduced `CourseLockDuration` to 5 frames for fast homing on close-range surface/sub targets.
  - `[SAMWH]`: Updated armor verses to 100% across all armor types (infantry, vehicles, heavy vessels, wood/steel/concrete structures, and walls).

---

## 🐛 Engine Bugfixes & Infiltration Logic

### 1. Concrete Bunker Invisible Placement Fix
- **The Bug**: When placing the Concrete Bunker (`CABUNK01`) from the sidebar, the structure was selectable on the map grid but completely invisible.
- **Root Cause**: Westwood never compiled or shipped a separate `.SHP` graphic file named `CABUNK01`—it only existed as a legacy text entry in the `.ini` files. Westwood created the actual 3D concrete bunker artwork and its construction animation as `NABNKR` and `NABNKRMK`. Without `Image=NABNKR` and a valid `Buildup` animation, the game engine placed the building in a construction state with no art to render.
- **Fix**: Added `Image=NABNKR` in `rulesmd.ini` and configured full construction buildup properties (`Buildup=NABNKRMK`, `DemandLoadBuildup=true`, `FreeBuildup=true`) along with all 8 muzzle flash offsets in `artmd.ini` (and `Image=GAPILL` in RA2). The bunker now visibly constructs and renders in all map theaters.

### 2. Spy Power Plant Blackout Fix
- **The Bug**: When a Spy entered a power plant (`GAPOWR`, `NAPOWR`, or `YAPOWR`), the power would not shut down.
- **Root Cause**: In the game binary (`BuildingClass::Spy_Effect` at `0x00452390` in `game.exe` / `0x004571E0` in `gamemd.exe`), the engine evaluates infiltration via an exclusive `if ... else if` chain:
  ```cpp
  if (BuildingType->Radar) {
      // 1. Radar Sabotage (resets radar, plays Eva "Radar Sabotaged")
      return; // Exits immediately!
  }
  else if (BuildingType->Power > 0) {
      // 2. Power Sabotage (blacks out victim power for SpyPowerBlackout frames)
      return;
  }
  ```
  `Radar=yes` and `SpySat=yes` were previously placed above power plants, causing the engine to classify them as radar stations. The engine triggered a radar sabotage and aborted immediately before reaching the power blackout code.
- **Fix**: Removed `Radar=yes` and `SpySat=yes` from all power plants in `rules.ini` and `rulesmd.ini`, and added `Spyable=yes` to `[CAPOWR]`. Power plants now reliably trigger the full ~1-minute power blackout (`SpyPowerBlackout=1000`).

### 3. Tech Airport Construction Yard Integration & Airfield Capabilities
- **The Issue**: Players capturing a map Tech Airport wanted to immediately start building base structures (functioning like an MCV) while also commanding air wings. However, in Westwood's engine, `FreeUnit` is never triggered when capturing pre-placed map structures, and buildings cannot combine multiple production queues.
- **The Solution**: Transformed `[CAAIRP]` into an active **Construction Yard**:
  - Added `ConstructionYard=yes`, `Factory=BuildingType`, and `EligibileForAllyBuilding=yes`.
  - Capturing the Tech Airport immediately unlocks the **Building** and **Defense** sidebar menus for whichever faction captures it, allowing immediate placement of Power Plants, Barracks, War Factories, Air Force Commands, and Defenses without needing an MCV.
  - Retained `Radar=yes` and included `CAAIRP` in `PrerequisiteRadar` under `[General]`.
  - Retained full 4-pad helipad servicing (`Helipad=yes`, `UnitReload=yes`, `NumberOfDocks=4`) so all friendly aircraft can land, reload missiles, and repair on the tarmac.
  - Retained the Allied Paradrop superweapon (`SuperWeapon=ParaDropSpecial`).

---

## 📁 Modified Files Reference

| File | Purpose | Key Modifications |
| :--- | :--- | :--- |
| **`rules.ini`** | Red Alert 2 core rules | Building and unit prerequisite overrides, IFV repair fixes, Tanya barrel damage, tech building parameters, bunker stats. |
| **`rulesmd.ini`** | Yuri's Revenge core rules | Yuri-specific prerequisites, Yuri tech buildings, Yuri power plant fixes, bunker stats, Navy SEAL unlock. |
| **`art.ini`** | RA2 artwork and animations | Cameo definitions and `DemandLoad=false` for buildable civilian/tech structures and bunkers. |
| **`artmd.ini`** | YR artwork and animations | Muzzle flashes 5–7 for bunkers, cameo assignments, building animation definitions. |

---

## 🔄 Installation & Restoration

1. **How It Works**:
   These `.ini` files reside in your root Red Alert 2 folder (`Command & Conquer Red Alert II`). The game engine automatically loads external `.ini` files in this directory with higher priority than internal `.mix` archives.
2. **Backing Up**:
   Keep a copy of these 4 files (`rules.ini`, `rulesmd.ini`, `art.ini`, `artmd.ini`) before making any further edits.
3. **Restoring Vanilla Gameplay**:
   Delete or rename `rules.ini`, `rulesmd.ini`, `art.ini`, and `artmd.ini`. The game will automatically fall back to the vanilla game data stored inside the `.mix` files.
