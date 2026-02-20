import { useCallback, useEffect, useRef, useState } from "react";

export interface GalleryImage {
  url: string;
  alt?: string;
}

interface ImageGalleryProps {
  images: GalleryImage[];
  initialIndex?: number;
  onClose: () => void;
}

function ImageGallery({ images, initialIndex = 0, onClose }: ImageGalleryProps) {
  const [currentIndex, setCurrentIndex] = useState(
    images.length > 0 ? Math.min(initialIndex, images.length - 1) : 0,
  );
  const overlayRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const goNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % images.length);
  }, [images.length]);

  const goPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  }, [images.length]);

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowRight") {
        goNext();
      } else if (e.key === "ArrowLeft") {
        goPrevious();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, goNext, goPrevious]);

  // Focus trap: keep focus within the overlay
  useEffect(() => {
    const handleFocusTrap = (e: FocusEvent) => {
      if (overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        closeButtonRef.current?.focus();
      }
    };
    document.addEventListener("focusin", handleFocusTrap);
    return () => document.removeEventListener("focusin", handleFocusTrap);
  }, []);

  if (images.length === 0) {
    return null;
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-label="Image gallery"
      aria-modal="true"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90"
      onClick={handleOverlayClick}
    >
      {/* Close button */}
      <button
        ref={closeButtonRef}
        onClick={onClose}
        aria-label="Close gallery"
        className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Main image area */}
      <div className="flex flex-1 items-center justify-center gap-4 px-16 py-8">
        {/* Previous button */}
        <button
          onClick={goPrevious}
          aria-label="Previous image"
          className="shrink-0 rounded-full bg-white/10 p-3 text-white transition-colors hover:bg-white/20"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        {/* Current image */}
        <div className="flex max-h-[70vh] max-w-4xl items-center justify-center">
          <img
            src={images[currentIndex].url}
            alt={images[currentIndex].alt ?? `Image ${currentIndex + 1}`}
            className="max-h-[70vh] max-w-full rounded-lg object-contain"
            loading="eager"
          />
        </div>

        {/* Next button */}
        <button
          onClick={goNext}
          aria-label="Next image"
          className="shrink-0 rounded-full bg-white/10 p-3 text-white transition-colors hover:bg-white/20"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Image counter */}
      <div className="mb-2 text-sm text-white/70" aria-live="polite">
        {currentIndex + 1} / {images.length}
      </div>

      {/* Thumbnail strip */}
      <div
        className="mb-4 flex max-w-full gap-2 overflow-x-auto px-4 pb-2"
        role="tablist"
        aria-label="Image thumbnails"
      >
        {images.map((image, index) => (
          <button
            key={index}
            role="tab"
            aria-selected={index === currentIndex}
            aria-label={image.alt ?? `Thumbnail ${index + 1}`}
            onClick={() => setCurrentIndex(index)}
            className={`shrink-0 overflow-hidden rounded-md border-2 transition-all ${
              index === currentIndex
                ? "border-white opacity-100"
                : "border-transparent opacity-50 hover:opacity-75"
            }`}
          >
            <img
              src={image.url}
              alt={image.alt ?? `Thumbnail ${index + 1}`}
              className="h-16 w-20 object-cover"
              loading={Math.abs(index - currentIndex) <= 2 ? "eager" : "lazy"}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

export default ImageGallery;
