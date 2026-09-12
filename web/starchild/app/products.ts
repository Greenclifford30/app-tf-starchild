export type Product = {
  slug: string;
  category: string;
  name: string;
  image: string;
  alternateImage?: string;
  alt: string;
  homeSummary: string;
  story: string[];
  price: number;
  colors: string[];
  sizes: string[];
  availability: "In stock" | "Limited availability";
  details: { label: string; value: string }[];
};

export const products: Product[] = [
  {
    slug: "stars-dont-see-tears",
    category: "T-shirt",
    name: "Stars Don't See Tears",
    image: "/products/stars_dont_see_tears_shirt.PNG",
    alt: "White Starchild T-shirt with star graphics, shown from the front and back",
    homeSummary: "A reminder that every trial shapes your strength.",
    price: 38,
    colors: ["White"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "In stock",
    details: [
      { label: "Fit", value: "Relaxed everyday fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "The child is wiping away tears, but the stars above remain bright. They do not witness the pain. They reflect the strength that comes after it. Every tear represents a lesson, and every trial is a step toward becoming who you are meant to be.",
      "The SC on the head symbolizes a mindset: a Starchild is not born into greatness. They are shaped by adversity. The message on the back reinforces that truth: The Starchild was never born, but made through trials and tribulations.",
    ],
  },
  {
    slug: "starchild-juneteenth-piece",
    category: "T-shirt",
    name: "Starchild Juneteenth Piece",
    image: "/products/starchild_juneteenth_shirt.png",
    alternateImage: "/products/starchild_juneteenth_shirt_2.png",
    alt: "Black Starchild Juneteenth T-shirt with colorful freedom and heritage artwork",
    homeSummary: "A tribute to freedom, strength, and legacy.",
    price: 42,
    colors: ["Black"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "Limited availability",
    details: [
      { label: "Fit", value: "Relaxed everyday fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "This Starchild Juneteenth Piece honors the strength, freedom, and legacy of those who paved the way for future generations. The broken chains symbolize liberation, while the bold colors represent culture, unity, and hope.",
      "At its core, the design reminds us that true freedom is more than history. It is a legacy to honor, protect, and carry forward. Honor the past. Celebrate the present. Build the future.",
    ],
  },
  {
    slug: "world-is-in-your-hands",
    category: "Long sleeve",
    name: "The World Is in Your Hands",
    image: "/products/the_world_is_in_your_hands_longsleeve_front.png",
    alternateImage: "/products/the_world_is_in_your_hands_longsleeve_back.png",
    alt: "White Starchild long-sleeve shirt with a green child and globe graphic on the front",
    homeSummary: "For curiosity, hope, and limitless potential.",
    price: 48,
    colors: ["White"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "In stock",
    details: [
      { label: "Fit", value: "Easy long-sleeve fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "Every Starchild starts with curiosity, hope, and the belief that anything is possible. The child holding the world symbolizes limitless potential: the power to dream beyond boundaries and create your own future.",
      "The message on the back reminds us that greatness is not something you are born with. It is built through every challenge, setback, and lesson life brings. A Starchild does not wait for the world to change. They grow strong enough to change it.",
    ],
  },
  {
    slug: "starchild-smiley-tee",
    category: "T-shirt",
    name: "Cropped Starchild Smiley Face Tee",
    image: "/products/starchild_smiley_shirt.png",
    alternateImage: "/products/starchild_smiley_shirt_back.png",
    alt: "White Starchild Smiley T-shirt with a multicolored smiley graphic on the front",
    homeSummary: "A bright reminder to keep smiling through it all.",
    price: 36,
    colors: ["White"],
    sizes: ["XS", "S", "M", "L", "XL"],
    availability: "In stock",
    details: [
      { label: "Fit", value: "Cropped, relaxed fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "This Cropped Starchild Smiley Face Tee is a reminder that joy is a choice, not a circumstance. The colorful smiley represents resilience: the ability to keep shining even after life's hardest moments.",
      "The message on the back, Regardless of what happened, keep smiling, reflects the Starchild mindset: staying hopeful, embracing growth, and refusing to let yesterday define today. A Starchild does not smile because life is perfect. They smile because brighter days are ahead.",
    ],
  },
  {
    slug: "divine-direction",
    category: "T-shirt",
    name: "Divine Direction",
    image: "/products/divine_direction_shirt.png",
    alt: "White Divine Direction Starchild T-shirt with faith-inspired artwork",
    homeSummary: "Guided by faith, ambition, and purpose.",
    price: 38,
    colors: ["White"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "In stock",
    details: [
      { label: "Fit", value: "Relaxed everyday fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "This design represents being guided by faith, driven by ambition, and protected through every step of the journey. The crosses represent faith, the stars represent dreams and direction, the dove represents peace and hope, and the chain around Made With Ambition represents the strength to keep pushing forward.",
      "Redeemed represents growth, second chances, and becoming a better version of yourself. Stay rooted in faith, move with purpose, chase your ambitions, and trust that your journey is leading somewhere greater.",
    ],
  },
  {
    slug: "love-in-motion",
    category: "Hoodie",
    name: "Love in Motion",
    image: "/products/love_in_motion_hoodie.PNG",
    alternateImage: "/products/love_in_motion_shirt.png",
    alt: "Dark brown Starchild Love in Motion hoodie with a cupid graphic and pink details",
    homeSummary: "Follow your heart. Move with purpose.",
    price: 68,
    colors: ["Espresso"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "Limited availability",
    details: [
      { label: "Fit", value: "Relaxed pullover fit" },
      { label: "Material", value: "Midweight cotton blend" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "This design represents moving through life with love, confidence, and intention. The cupid symbolizes love, while the arrow represents clear direction and going straight toward what your heart desires. Straight to the Heart is a reminder to stay genuine, follow your heart, and never be afraid to pursue what truly matters to you.",
      "The dark brown color gives the piece a vintage, timeless feeling, while the pink accents bring out the softer side of love and emotion. Starchild branding ties it together as a message of being your own person while still leading with heart. Follow your heart. Move with purpose. Love deeply. Never lose yourself along the way.",
    ],
  },
  {
    slug: "call-unto-him-longsleeve",
    category: "Long sleeve",
    name: "Call Unto Him Starchild Longsleeve",
    image: "/products/call_unto_him_crewneck.png",
    alternateImage: "/products/call_unto_him_crewneck_2.png",
    alt: "White Starchild Call Unto Him long-sleeve shirt with orange artwork",
    homeSummary: "A reminder to reach for guidance, strength, and peace.",
    price: 48,
    colors: ["White"],
    sizes: ["S", "M", "L", "XL", "2XL"],
    availability: "In stock",
    details: [
      { label: "Fit", value: "Easy long-sleeve fit" },
      { label: "Material", value: "Cotton jersey" },
      { label: "Care", value: "Machine wash cold, inside out" },
    ],
    story: [
      "Call Unto Him represents turning to God in every season of life: not only when things are going wrong, but also when we need guidance, strength, peace, or direction. The child with raised arms represents faith, surrender, and trust.",
      "The Starchild name on the sleeve connects the message to the brand's spirituality, emotion, and self-expression. The orange artwork represents warmth, energy, and hope. No matter where life takes you, never be afraid to call unto Him. There is always something greater to reach toward.",
    ],
  },
];

export const featuredProducts = products.filter((product) =>
  ["starchild-smiley-tee", "world-is-in-your-hands", "stars-dont-see-tears", "love-in-motion"].includes(product.slug),
);

export function getProduct(slug: string) {
  return products.find((product) => product.slug === slug);
}
