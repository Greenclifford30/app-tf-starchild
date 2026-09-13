type BrandLogoProps = {
  className?: string;
  decorative?: boolean;
};

export default function BrandLogo({ className = "brand-logo", decorative = true }: BrandLogoProps) {
  return (
    <Image
      className={className}
      src="/Starchild_logo_transparent.svg"
      alt={decorative ? "" : "Starchild Clothing"}
      aria-hidden={decorative || undefined}
      width={829}
      height={1032}
    />
  );
}
import Image from "next/image";
