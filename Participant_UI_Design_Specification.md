# HackGuard AI - Participant UI Design Specification

**Document Version:** 1.0  
**Design Style:** High-Contrast Dual Theme (Dark Navigation + Soft Light Canvas + Pastel Metric Cards)  
**Target Screen:** Participant Dashboard & Submission Hub  

---

## 1. Visual Architecture & Design System

The Participant UI is modeled after modern high-end fintech dashboards, prioritizing readability, soft pastel data visualizers, and clear action callouts.

```
+----------------------------------------------------------------------------------------------------+
|  SIDEBAR    |  HEADER: Participant Overview            [ Search ]  [ 🔔 3 ]  [ 👤 Team Nova ⌄ ] |
| (Dark Nav)  |--------------------------------------------------------------------------------------+
|             |  MAIN SCORE WIDGET                      | PASTEL METRIC CARDS                        |
| [ ⚡ Logo ] |  [ Ice Blue Card ]                      | [ Lavender ]  [ Mint Green ]  [ Cream ]    |
|             |  Overall AI Score: 88.5 / 100           | Submission    Plagiarism      Leaderboard  |
| [ 📊 Dash ] |  (Interactive Score Graph)              | Status        Risk (0.2%)     Rank #3      |
| [ 👥 Team ] |-----------------------------------------+--------------------------------------------|
| [ 🚀 Submit]|  LIVE HACKATHON LEADERBOARD             | ACTION CALLOUT CARD (Dark Card)            |
| [ 🏆 Rank ] |  Rank | Team Name  | Score | Status     | "Submit Updated Repository & Demo Video"   |
| [ ⚙️ Config]|  #1   | CyberCrew  | 92.4  | 🟢 Clean   | "Deadline in 04h 12m"                      |
|             |  #2   | AI-Knights | 90.1  | 🟢 Clean   | [ 🚀 Submit Project Now ] (Pill CTA)       |
+----------------------------------------------------------------------------------------------------+
```

### Color Palette Tokens
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--sidebar-bg` | `#18191C` | Deep Charcoal Sidebar Background |
| `--canvas-bg` | `#F4F6FA` | Soft Off-White Main Canvas Background |
| `--card-bg` | `#FFFFFF` | Primary Widget Background |
| `--ice-blue-bg` | `#E8F2FF` | Overall Score Hero Card Tint |
| `--lavender-bg` | `#F0EBF9` | Submission Status Card Tint |
| `--mint-green-bg` | `#E6F7F0` | Plagiarism Risk Card Tint |
| `--cream-yellow-bg` | `#FEF9E7` | Leaderboard Rank Card Tint |
| `--dark-banner-bg` | `#18191C` | Bottom Right CTA Callout Card |
| `--accent-blue` | `#2B7FFF` | Primary CTA Button & Graphs |
| `--text-primary` | `#111827` | Headings & Primary Metric Values |
| `--text-secondary` | `#6B7280` | Labels & Subtitles |

---

## 2. Layout Breakdown & Components

### 2.1 Left Sidebar Navigation (`--sidebar-bg: #18191C`)
* **Width:** `240px` fixed vertical bar.
* **Top Header:** Rounded Cream Brand Badge (`#FDF8E2`) with HackGuard AI Icon.
* **Nav Options:**
  * 📊 **Dashboard / Overview** (Active State)
  * 👥 **Team Management**
  * 🚀 **Project Submission**
  * 📑 **AI Feedback Report**
  * 🏆 **Live Leaderboard**
  * ⚙️ **Settings**
* **Bottom Profile:** Compact Logout / Switch Role trigger.

---

### 2.2 Top Header Bar
* **Page Title:** Bold 28px `Overview`.
* **Right Controls:**
  * Search Bar (`220px` width, input with icon).
  * Notification Bell with active unread badge (`🔔`).
  * User Profile Pill: Avatar thumbnail + Team Name (`"Zoia M. (Team Nova) ⌄"`).

---

### 2.3 Hero Metrics Section (Top Row)

#### Widget 1: Main AI Score Card (`#E8F2FF` Ice Blue)
* **Metric:** `88.5 / 100` Overall AI Score.
* **Visual:** Interactive smooth line chart showing build-over-build score updates.
* **Sub-metrics:** Technical Score: `90`, Innovation: `85`, UI/UX: `88`.

#### Widget 2: Submission Status Card (`#F0EBF9` Lavender)
* **Icon:** 💜 Git/Repository Icon.
* **Status Value:** `Verified & Synced`.
* **Subtitle:** GitHub repository linked (`main` branch).

#### Widget 3: Plagiarism Risk Card (`#E6F7F0` Mint Green)
* **Icon:** 💚 Shield/Security Icon.
* **Metric:** `0.2% Low Risk`.
* **Badge:** `Passed AST Check` in dark green pill tag.

#### Widget 4: Leaderboard Rank Card (`#FEF9E7` Cream Yellow)
* **Icon:** 💛 Trophy Icon.
* **Metric:** `#3 of 142`.
* **Indicator:** `▲ +2 positions` since last build run.

---

### 2.4 Bottom Grid Section

#### Left Column: Live Hackathon Leaderboard Table (`#FFFFFF` Card)
* **Header:** *"Top Competing Teams"* + Filter dropdown (`Top Gainers ⌄`, `24h ⌄`).
* **Table Columns:** Rank, Team Name, Tech Stack, Score, Plagiarism Risk, Build Status.
* **Styling:** Soft rows with hover highlight effect, rounded avatar icons, and green/yellow risk pill tags.

#### Right Column: Action Callout Card (`#18191C` Dark Card)
* **Background:** Deep Charcoal card matching sidebar with subtle white grid accent.
* **Headline:** *"Earn Top Rank — Submit Updated Code & Video!"*
* **Body:** *"Final submission window closes in 04h 12m. Run Docker Sandbox validation before locking."*
* **Primary Button:** Light Blue rounded pill button `[ 🚀 Submit Project Now ]`.

---

## 3. Micro-Interactions & Styling Specs

* **Border Radius:** `24px` on main container frames and primary cards; `16px` on inner metric pills.
* **Hover Animations:** `transform: translateY(-3px)` with smooth `200ms ease-out` transition on metric cards.
* **Status Badges:** Pulsing green status dot (`🟢`) for clean submissions.
* **Typography:** `Plus Jakarta Sans` or `Outfit` with crisp font weights (`700` headings, `600` values, `500` body text).
