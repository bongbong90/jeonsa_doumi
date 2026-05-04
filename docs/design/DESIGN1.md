---
name: Transcription Assistant
colors:
  surface: '#faf8ff'
  surface-dim: '#dad9e1'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3fa'
  surface-container: '#eeedf4'
  surface-container-high: '#e9e7ef'
  surface-container-highest: '#e3e1e9'
  on-surface: '#1a1b21'
  on-surface-variant: '#444651'
  inverse-surface: '#2f3036'
  inverse-on-surface: '#f1f0f7'
  outline: '#757682'
  outline-variant: '#c5c5d3'
  surface-tint: '#4059aa'
  primary: '#00236f'
  on-primary: '#ffffff'
  primary-container: '#1e3a8a'
  on-primary-container: '#90a8ff'
  inverse-primary: '#b6c4ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#4b1c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#6e2c00'
  on-tertiary-container: '#f39461'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#264191'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdbcb'
  tertiary-fixed-dim: '#ffb691'
  on-tertiary-fixed: '#341100'
  on-tertiary-fixed-variant: '#773205'
  background: '#faf8ff'
  on-background: '#1a1b21'
  surface-variant: '#e3e1e9'
typography:
  display-metrics:
    fontFamily: Public Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Public Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  log-text:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: -0.01em
  label-caps:
    fontFamily: Public Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  gutter: 20px
  sidebar_width: 280px
---

## Brand & Style
The design system is engineered for professional environments where accuracy and endurance are paramount. The brand personality is rooted in **Trustworthy Precision**, ensuring that the user feels supported by an efficient, stable tool during the cognitive load of transcription. 

The visual style is **Corporate Modern with a Minimalist focus**. It prioritizes information density and readability over decorative flourishes. To evoke the "Flow from Sound to Text," the UI utilizes a motif of transitioning linear elements: rhythmic, organic audio waveforms that settle into structured, horizontal document lines. This transition signifies the transformation of raw data into organized knowledge. The interface avoids distractions, using purposeful whitespace to separate the acoustic workspace from the editorial workspace.

## Colors
The palette is centered on a **Deep Professional Blue** to anchor the user's focus and represent action and stability. Neutral tones are derived from **Soft Slate and Cool Grays**, creating a low-strain environment for extended use. 

- **Primary Blue:** Used for primary actions, active states, and progress indicators.
- **Surface Grays:** The main workspace uses the lightest cool gray to minimize glare, while sidebars and toolbars use a slightly deeper slate to define boundaries without heavy lines.
- **Muted Status:** Status colors are desaturated to ensure they communicate information (Complete, Danger, Warning) without causing visual alarm.

## Typography
This design system prioritizes Korean legibility. While **Public Sans** provides a stable, institutional structure for headings and metrics, **Inter** (or a local equivalent like **Pretendard**) is used for the core transcription logs to ensure high readability and neutral character shaping.

- **Metrics & Numbers:** Use bold Public Sans for dashboard counters to convey certainty.
- **Transcription Logs:** Increased line-height (28px) and slightly tighter letter-spacing are applied to long-form text to assist the eye in tracking horizontal lines across the desktop screen.
- **Hierarchy:** Clear distinction is maintained by using weight shifts rather than dramatic size increases.

## Layout & Spacing
The layout follows a **Fluid Grid** model optimized for Windows desktop environments, allowing the transcription editor to expand while sidebars remain anchored. 

- **Grid:** A 12-column system is used for the main dashboard views, while a 2-pane layout (Navigation/Editor) is preferred for the active transcription task.
- **Rhythm:** A 4px baseline grid ensures alignment. 24px (md) is the standard padding for containers to maintain a sense of openness.
- **Margins:** Outer page margins are fixed at 40px (lg) to provide "breathing room" against the OS window edges.

## Elevation & Depth
Depth in this design system is communicated through **Tonal Layering and Low-Contrast Outlines** rather than shadows. 

- **Layering:** The furthest background is the lightest (#F8FAFC). Interactive "cards" or work areas are placed on surfaces with subtle 1px borders (#E2E8F0).
- **Interactivity:** On hover, elements do not "lift" with shadows. Instead, they shift in background color or border intensity (from #E2E8F0 to #CBD5E1).
- **Depth:** Modal windows or pop-overs use a single, very soft, high-diffusion shadow (0px 10px 25px rgba(0,0,0, 0.05)) to separate them from the main workspace.

## Shapes
The shape language is **Soft and Professional (0.25rem / 4px)**. This choice balances the rigidity of a technical tool with the approachability of modern software.

- **Standard Elements:** Buttons, input fields, and checkboxes use the 4px base radius.
- **Container Elements:** Large dashboard cards or panels use `rounded-lg` (8px) to soften the overall interface architecture.
- **Motif Integration:** The waveform elements use rounded line caps to mirror the shape language of the buttons.

## Components
- **Buttons:** Primary buttons are solid Deep Blue with white text. Secondary buttons are outlined with a 1px slate border. All have a 4px corner radius.
- **Transcription Cards:** Low-elevation containers with a subtle left-accent border in Primary Blue to indicate the active speaking segment.
- **Audio Waveform:** Integrated into the playhead. The waveform uses a two-tone blue (Primary for played, Light Blue for remaining) with a vertical needle indicator.
- **Status Chips:** Small, pill-shaped indicators with desaturated background tints and darker text (e.g., Soft Green background with Deep Emerald text for "Completed").
- **Input Fields:** Flat design with a 1px border. Focus state is indicated by a 2px Primary Blue border, never a shadow.
- **Document Motif:** Subtle horizontal hair-lines are used in the background of the editor to simulate a lined document, guiding the eye during text entry.