# HackGuard AI - Organizer UI Design Specification

**Document Version:** 1.0  
**Design Style:** High-Contrast Dual Theme (Dark Navigation + Soft Light Canvas + Coral/Amber/Purple Metric Cards)  
**Target Screen:** Organizer Control Hub, Rubric Configurator & Fraud Monitor  
**PRD Module Mapping:** Module 13 (Organizer Dashboard), Section 7 (Rubric Configuration), Module 6 (Plagiarism Alerts), Module 12 (Leaderboard Management)  

---

## 1. Visual Architecture & Design System

The Organizer UI shares the exact visual skeleton as the Participant UI, ensuring a unified platform experience while providing high-priority visual alerts for fraud detection and rubric customization.

```
+----------------------------------------------------------------------------------------------------+
|  SIDEBAR    |  HEADER: Organizer Command Center        [ Search ]  [ 🔔 5 ]  [ 👤 Admin (IIT) ⌄ ] |
| (Dark Nav)  |--------------------------------------------------------------------------------------+
|             |  HERO METRIC CARDS                                                                   |
| [ ⚡ Logo ] |  [ Soft Blue ]       [ Lavender ]        [ Coral Red ]          [ Emerald ]          |
|             |  Total Teams         Evaluation Progress  Fraud & Plagiarism     Leaderboard State    |
| [ 📊 Dash ] |  142 Registered      85% Evaluated       3 Flagged Submissions  LIVE & UPDATING      |
| [ ⚙️ Rubric]|------------------------------------------+-------------------------------------------|
| [ 🛡️ Fraud ]|  INTERACTIVE RUBRIC CONFIGURATOR         | FRAUD ALERTS & SUBMISSION MONITOR         |
| [ 🏆 Leader]|  Technical Complexity: 30% [========---] | Team Alpha  | 84% AST Match | ⚠️ Flagged   |
| [ 📄 Report]|  Innovation:           20% [======-----] | Team Beta   | 0.2% AST Match| 🟢 Clean     |
| [ ⚙️ Config]|  UI/UX:                15% [====-------] | Team Gamma  | 12% AST Match | 🟢 Clean     |
|             |  [ 💾 Save Rubric & Recalculate Scores ] | [ 📥 Export CSV ]  [ 🚀 Publish Ranks ]    |
+----------------------------------------------------------------------------------------------------+
```

### Color Palette Tokens
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--sidebar-bg` | `#18191C` | Deep Charcoal Sidebar Background |
| `--canvas-bg` | `#F4F6FA` | Soft Off-White Main Canvas Background |
| `--card-bg` | `#FFFFFF` | Primary Widget Background |
| `--coral-red-bg` | `#FEE2E2` / `#EF4444` | Fraud & High-Risk Plagiarism Alert Tint |
| `--amber-bg` | `#FEF3C7` / `#F59E0B` | Warning / Medium Risk Alert Tint |
| `--soft-blue-bg` | `#E8F2FF` / `#2B7FFF` | Total Teams & Registration Tint |
| `--purple-bg` | `#F0EBF9` / `#8B5CF6` | Evaluation Progress Metrics Tint |
| `--accent-blue` | `#2B7FFF` | Save/Action Buttons & Sliders |
| `--text-primary` | `#111827` | Headings & Primary Metric Values |

---

## 2. Layout Breakdown & Components

### 2.1 Left Sidebar Navigation (`#18191C`)
* **Top Header:** Rounded Cream Brand Badge (`#FDF8E2`) + Organizer Admin Tag.
* **Nav Options:**
  * 📊 **Organizer Overview** (Active State)
  * ⚙️ **Rubric Configurator**
  * 🛡️ **Plagiarism & Fraud Monitor**
  * 🏆 **Leaderboard & Result Publisher**
  * 📄 **Analytics & PDF/CSV Reports**
  * ⚙️ **Event Settings**

---

### 2.2 Top Hero Metrics Section

#### Widget 1: Total Teams Card (`#E8F2FF` Soft Blue)
* **Metric:** `142 Teams` (`468 Participants`).
* **Sub-text:** Registration status: **Closed**.

#### Widget 2: Evaluation Progress Card (`#F0EBF9` Purple)
* **Metric:** `85% Complete` (`121/142 Evaluated`).
* **Visual:** Smooth progress bar indicating automated execution progress.

#### Widget 3: Fraud & Plagiarism Alert Card (`#FEE2E2` Coral Red)
* **Metric:** `3 Flagged Submissions`.
* **Badge:** `Action Required` in bold red pill tag.

#### Widget 4: Leaderboard State Card (`#E6F7F0` Mint Green)
* **Status:** `LIVE & UPDATING`.
* **Action Toggle:** Switch between `Private Preview` and `Public Live`.

---

### 2.3 Main Grid Section

#### Left Column: Interactive Evaluation Rubric Configurator (`#FFFFFF` Card)
* **Purpose:** Allows organizers to dynamically adjust weighted criteria (PRD Section 7).
* **Interactive Sliders:**
  * Technical Complexity: `30%`
  * Innovation: `20%`
  * UI/UX: `15%`
  * Business Impact: `15%`
  * Documentation: `10%`
  * Presentation: `10%`
* **Real-time Indicator:** Auto-calculates total percentage sum ($100\%$).
* **Primary Action:** `[ 💾 Save Rubric & Recalculate Scores ]` button.

#### Right Column: Fraud Alerts & Submission Monitor (`#FFFFFF` Card)
* **Header:** *"Real-Time Submissions & Fraud Feed"* + Filter (`Show Flagged Only`).
* **Data Table:**
  * Team Name & GitHub Repo Link.
  * AST Code Similarity % (Flagged if $> 60\%$).
  * Static Analysis Security Risks (`Semgrep` flags).
  * Docker Sandbox Execution Status (`Passed` / `Failed`).
  * Action Button: `[ Audit Code ]` or `[ Dismiss Alert ]`.

---

### 2.4 Bottom Action Toolbar
* `[ 📥 Export Full Results (CSV/PDF) ]`
* `[ 🚀 Publish Final Hackathon Winners ]` (triggers public leaderboard lock).
