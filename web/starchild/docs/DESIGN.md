# Starchild design foundation

## Design read

**Reading this as:** a premium, community-led sustainable apparel storefront for style-conscious shoppers, with an optimistic celestial language grounded in crisp, modern retail design.

**Design dials:** `DESIGN_VARIANCE: 7` · `MOTION_INTENSITY: 4` · `VISUAL_DENSITY: 3`

The source references consistently communicate star imagery, a deep-blue/yellow palette, expressive clothing photography, sustainability, and social participation. They do not yet form one system: navy ranges from `#000080` to `#0A1C2E`, and the display face changes across pages. This foundation retains the strongest shared cues and removes those inconsistencies.

## The idea: "Solar after dark"

Starchild should feel like a night-time creative studio rather than a generic boho or space shop: midnight-blue structure, a precise solar-yellow spark, and candid, tactile photography. The visual tension is intentional: considered enough for a premium garment, bright enough to feel young and social.

### Brand principles

1. **Personal, not precious.** The clothing and the people wearing it lead; celestial elements are accents, never decoration for decoration's sake.
2. **Optimistic precision.** Strong grid, generous empty space, crisp type, and one bright signature color.
3. **Proof over claims.** Sustainability content should show material, maker, and care details rather than relying on broad green-language.
4. **Community has equal status.** Customer imagery belongs beside campaign imagery, with clear credit and consent.

## Visual system

### Color

| Role | Token | Value | Use |
| --- | --- | --- | --- |
| Midnight | `--color-ink` | `#10172B` | Primary text, footer, primary buttons |
| Orbit | `--color-navy` | `#182D61` | Navigation, secondary dark surfaces |
| Solar | `--color-solar` | `#F9E006` | Brand accent, active state, small badges, focus motif |
| Daylight | `--color-canvas` | `#F7F8FC` | Main page background |
| Cloud | `--color-surface` | `#FFFFFF` | Cards, sheets, inputs |
| Blue haze | `--color-tint` | `#E8EEFF` | Quiet selected/announcement surfaces |
| Slate | `--color-muted` | `#596176` | Secondary text |
| Line | `--color-line` | `#DCE1EC` | Borders and dividers |
| Signal red | `--color-danger` | `#B42318` | Errors only |

Solar is the one brand accent. It is not a text color on white, and white text is never placed on Solar. The primary purchase action is Midnight with white text; Solar is the small, memorable punctuation around it.

### Typography

Use the already configured **Geist** family for every interface surface. It keeps browsing and checkout fast, legible, and cohesive. The wordmark may use a custom lockup later; until then use `Geist` 700, italic, with tight tracking rather than a page-specific script font.

| Role | Desktop | Mobile | Weight / line height |
| --- | ---: | ---: | --- |
| Display | 64px | 44px | 650 / 0.98 |
| H1 | 48px | 36px | 650 / 1.02 |
| H2 | 32px | 28px | 600 / 1.12 |
| H3 | 20px | 20px | 600 / 1.25 |
| Body | 16px | 16px | 400 / 1.55 |
| Supporting | 14px | 14px | 450 / 1.45 |
| Label | 12px | 12px | 600 / 1.2, `0.06em` tracking |

Headlines are sentence case, direct, and limited to two lines at desktop. Avoid all-caps headline treatments. Labels can use small uppercase only where they identify a real category, such as `NEW DROP` or `LOW IMPACT MATERIAL`.

### Layout and rhythm

- **Content width:** 1440px maximum; standard gutters 32px desktop, 20px mobile.
- **Grid:** 12 columns desktop; 6 tablet; 4 mobile. Product grids become 4 / 3 / 2 columns respectively.
- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64, 96, 128px.
- **Radius:** 4px for controls; 8px for product imagery and panels; full-pill only for filter chips. Do not mix arbitrary rounded shapes.
- **Elevation:** primarily borders and space. A hoverable product may use `0 12px 28px rgba(16, 23, 43, .10)`; no persistent heavy shadows.

### Motifs and texture

Use a sparse 1px star/cross motif only in campaign and editorial contexts: no more than three marks in a viewport. It can anchor a crop, tag a new collection, or appear in empty space near the wordmark. It must not be a repeating background or a substitute for photography.

## Components

| Component | Definition |
| --- | --- |
| Header | 72px desktop / 64px mobile, white or Canvas background, one-line navigation. Left: wordmark. Centre: Shop, New arrivals, About. Right: Search, Account, Bag; bag count is a small Solar disc. |
| Buttons | 44px minimum height; 4px radius. Primary is Ink with white text; hover lifts 1px and darkens. Secondary is surface with Ink border. Solar is reserved for icon emphasis and selected chips. |
| Product card | Image first at 3:4. Beneath: category label, product name, price, optional color swatches. Quick add appears only on hover/focus desktop and as a visible compact control on touch. No card frame around the entire item. |
| Filters | Desktop: a left rail or horizontal utility row, never both. Mobile: one `Filter & sort` sheet trigger with active-filter count. Selected chips are Tint with Ink text. |
| Product detail | Two-column gallery + buying panel. Buying panel includes name, price, color, size, size guide, quantity, primary Add to bag, shipping/returns link. The selected variant receives both a border and text state; color alone cannot communicate selection. |
| Inputs | Label above field, 44px minimum height, Surface fill, Line border, 2px Solar focus ring with Ink offset. Inline error is Signal red below the field. |
| Sustainability proof | A compact, structured section: material composition, origin/maker, care and expected wear. Link to a fuller impact page; do not add unverified impact metrics. |
| Empty / loading | Product-shaped skeletons for loading. An empty bag shows one short line and a `Shop new arrivals` action; no illustration required. |

## Photography and content art direction

Product images are the design system's most important asset. Use a deliberate mix:

- **Product listing:** clean 3:4 full-look or garment shots, consistent crop and subdued studio/background treatment.
- **Campaign:** directional, low-saturation city/night or late-day natural light, real texture, motion, and close crops. Midnight may appear in styling or setting, but images should not be artificially blue-washed.
- **Community:** candid vertical imagery in a varied masonry grid. Keep the image grid clean; show attribution in the opened post rather than on every tile.
- **Editorial/sustainability:** material and process details (hands, fabric, construction), avoiding generic leaves, globes, or stock “eco” imagery.

All product imagery needs descriptive alt text with garment type, color, and relevant view. Community photos require consent and source attribution before publication.

## Page direction

### Home

1. Split hero: short campaign line, `Shop the collection`, and one full-bleed campaign image.
2. New arrivals: four product cards, then a single `Shop new arrivals` link.
3. A full-width community/campaign image block with one editorial statement.
4. Three proof points: materials, makers, made to wear; each links to evidence.
5. Community preview: asymmetric six-image grid and `Join the community`.
6. Email signup, then the full footer.

### Shop / collection

Clear category title and item count; filtering that is simple on mobile; a dense, image-led product grid. Product cards should make both garment and price scannable without requiring hover.

### Product detail

Images answer fit and fabric questions. The purchase panel stays calm and unambiguous. Trust details appear below Add to bag, while product story and proof sit below the primary decision area.

### About / impact

Lead with the founder/design perspective from the reference material, then explain design philosophy and substantiated production practices. It is an editorial page, not a wall of centered claims.

### Community and contact

Community is a photo-led participatory page with a clear submission/follow action. Contact is a quiet utility page with a concise form, response expectation if known, and direct email.

## Interaction and accessibility

- Use 150–200ms opacity/transform transitions for hover and page-local reveals; respect `prefers-reduced-motion`.
- Never hide an action needed to shop on touch devices.
- Provide visible keyboard focus and 44px targets for all pointer controls.
- Maintain WCAG AA contrast; especially do not use Solar for small type on a light background.
- Preserve scroll position and filter selections when a shopper opens and returns from a product.
- Use real buttons for actions and real links for navigation; all icon-only controls need accessible labels.

## Decisions for review

1. Approve the **midnight + solar** visual direction and the removal of page-specific script fonts.
2. Confirm the customer group: the provided shop reference includes Men/Women/Accessories while the story reference emphasises dresses and tailored separates. The proposed navigation is intentionally category-neutral until merchandising confirms the taxonomy.
3. Provide or commission a final wordmark and the first campaign/product photo set. These should be created before visual implementation, since they determine the feel more than any CSS treatment.
