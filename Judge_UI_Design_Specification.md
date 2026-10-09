# HackEval - Judge UI Design Specification

**Document Version:** 1.0  
**Design Style:** High-Contrast Dual Theme (Dark Navigation + Soft Light Canvas + Emerald/Teal/Ice Blue Metric Cards)  
**Target Screen:** Judge Review Portal, AI Report Reader & Score Override Console  
**PRD Module Mapping:** Module 14 (Judge Dashboard), Module 5 (AI Evaluation), Module 8 (Static Analysis), Module 9 (Docker Sandbox Logs), Module 11 (Demo Video Transcripts)  

---

## 1. Visual Architecture & Design System

The Judge UI shares the same sleek, high-contrast visual shell as the Participant and Organizer dashboards, providing judges with deep AI report insights, raw build log access, and clean manual score override controls.

```
+----------------------------------------------------------------------------------------------------+
|  SIDEBAR    |  HEADER: Judge Audit & Review Portal     [ Search Team ] [ 🔔 2 ] [ 👤 Prof. Alan ⌄ ]|
| (Dark Nav)  |--------------------------------------------------------------------------------------+
|             |  HERO METRIC CARDS                                                                   |
| [ ⚡ Logo ] |  [ Soft Teal ]       [ Emerald Green ]    [ Ice Blue ]           [ Soft Purple ]      |
|             |  Pending Reviews     AI Confidence Score  Overridden Scores      Current Queue       |
| [ 📊 Dash ] |  8 Submissions       94% High Accuracy    2 Teams Overridden     Team Beta (#4)      |
| [ 📑 Audit ]|------------------------------------------+-------------------------------------------|
| [ ⚖️ Override|  MULTIMODAL AI REPORT READER             | MANUAL SCORE OVERRIDE & FEEDBACK PANEL    |
| [ 💬 Feedback|  [ AI Summary ] [ Code ] [ Docker ] [ Video] | Tech Complexity: 28/30 [========---]    |
| [ 🏆 Final ]|  • Architecture: Microservices Clean    | Innovation:      18/20 [======-----]    |
| [ ⚙️ Config]|  • Security: 0 High Vulnerabilities     | UI/UX:           14/15 [====-------]    |
|             |  • Video STT: Covered 95% claimed features| Override Reason: "Impressive UI demo"   |
|             |  [ 📂 View Full Repo ] [ 📜 Build Logs ] | [ 💾 Save Score Override & Finalize ]     |
+----------------------------------------------------------------------------------------------------+
```

### Color Palette Tokens
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--sidebar-bg` | `#18191C` | Deep Charcoal Sidebar Background |
| `--canvas-bg` | `#F4F6FA` | Soft Off-White Main Canvas Background |
| `--card-bg` | `#FFFFFF` | Primary Widget Background |
| `--emerald-green-bg` | `#E6F7F0` / `#10B981` | AI High Confidence & Approved Score Tint |
| `--teal-bg` | `#E0F2FE` / `#0284C7` | Pending Reviews Tint |
| `--ice-blue-bg` | `#E8F2FF` / `#2B7FFF` | Overridden Scores Count Tint |
| `--purple-bg` | `#F0EBF9` / `#8B5CF6` | Current Queue Focus Tint |
| `--accent-emerald` | `#10B981` | Final Approval & Save Buttons |
| `--text-primary` | `#111827` | Headings & Primary Metric Values |

---

## 2. Layout Breakdown & Components

### 2.1 Left Sidebar Navigation (`#18191C`)
* **Top Header:** Rounded Cream Brand Badge (`#FDF8E2`) + Judge Badge.
* **Nav Options:**
  * 📊 **Judge Dashboard / Queue** (Active State)
  * 📑 **AI Report Audit Reader**
  * ⚖️ **Score Override Console**
  * 💬 **Participant Feedback Log**
  * 🏆 **Final Winner Approval**
  * ⚙️ **Settings**

---

### 2.2 Top Hero Metrics Section

#### Widget 1: Pending Reviews Card (`#E0F2FE` Soft Teal)
* **Metric:** `8 Submissions Left`.
* **Subtitle:** Out of 25 assigned judge reviews.

#### Widget 2: AI Confidence Score Card (`#E6F7F0` Emerald Green)
* **Metric:** `94% High Confidence`.
* **Badge:** `Low Variance` pill tag.

#### Widget 3: Overridden Scores Card (`#E8F2FF` Ice Blue)
* **Metric:** `2 Overrides Applied`.
* **Subtitle:** Manual score adjustments logged.

#### Widget 4: Current Active Review Focus (`#F0EBF9` Purple)
* **Active Target:** `Team Beta (#4 Rank)`.
* **Action:** Direct jump to team submission files.

---

### 2.3 Main Grid Section

#### Left Column: Multimodal AI Report Reader (`#FFFFFF` Card)
* **Tab Controls:** `[ 🤖 AI Executive Summary ]`, `[ 🛡️ Static Code Report ]`, `[ 🐳 Docker Sandbox Logs ]`, `[ 🎥 Video Transcript (Whisper) ]`.
* **Content View:**
  * **AI Summary:** Auto-extracted strengths, architecture evaluation, and missing documentation alerts.
  * **Static Code Report:** `Semgrep` & `ESLint` vulnerability count and code smell breakdown.
  * **Docker Logs:** Container build time, unit test pass rate ($12/12$ tests passed), and CPU/RAM consumption.
  * **Video Transcript:** Whisper Speech-to-Text transcript with matched feature claims.

#### Right Column: Manual Score Override & Feedback Console (`#FFFFFF` Card)
* **Parameter Sliders (Pre-filled with AI Scores):**
  * Technical Complexity: `28 / 30`
  * Innovation: `18 / 20`
  * UI/UX: `14 / 15`
  * Business Impact: `13 / 15`
  * Documentation: `9 / 10`
  * Presentation: `9 / 10`
* **Override Justification Box:** Mandatory text area if slider is adjusted (*"Increased UI score by +2 points due to exceptional live demo polished polish."*).
* **Qualitative Feedback Field:** Participant-facing feedback comment box.
* **Primary Action Button:** `[ 💾 Save Override & Approve Project ]`.

---

## 3. Workflow Summary for Judges

1. Select team from **Pending Review Queue**.
2. Audit the **Multimodal AI Report** (Repo analysis, build logs, video transcript).
3. Verify baseline AI scores; optionally adjust sliders with justification.
4. Add qualitative mentor feedback and click **Approve Project**.
