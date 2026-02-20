import { Link } from "react-router-dom";

function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-16">
      <div className="max-w-md text-center">
        <h1 className="mb-2 text-6xl font-bold text-brand-blue">404</h1>
        <h2 className="mb-4 text-2xl font-semibold text-text-primary">Page Not Found</h2>
        <p className="mb-8 text-text-secondary">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link
          to="/"
          className="inline-block rounded-md bg-brand-blue px-6 py-2 font-semibold text-white transition-colors hover:bg-blue-700"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}

export default NotFoundPage;
