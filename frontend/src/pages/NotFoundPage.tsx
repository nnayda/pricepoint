import { Link } from "react-router-dom";

function NotFoundPage() {
  return (
    <div
      className="font-db-sans flex min-h-screen flex-col items-center justify-center px-4"
      style={{ backgroundColor: "var(--th-bg-base)" }}
    >
      <h1 className="mb-2 text-6xl font-bold" style={{ color: "var(--color-db-accent)" }}>
        404
      </h1>
      <h2 className="mb-4 text-2xl font-semibold" style={{ color: "var(--color-db-text-primary)" }}>
        Page Not Found
      </h2>
      <p className="mb-8 max-w-md text-center" style={{ color: "var(--color-db-text-secondary)" }}>
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="inline-block rounded-md px-6 py-2 font-semibold text-white transition-colors"
        style={{ backgroundColor: "var(--color-db-accent)" }}
      >
        Back to Home
      </Link>
    </div>
  );
}

export default NotFoundPage;
