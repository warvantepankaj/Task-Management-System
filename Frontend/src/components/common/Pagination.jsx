import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

/**
 * Compact pagination control: first / prev / current / next / last + total count.
 *
 * Props:
 *   page         (number)  1-indexed current page
 *   totalPages   (number)  total number of pages (>= 1)
 *   total        (number)  total record count (for the summary text)
 *   pageSize     (number)  page size (for the summary text)
 *   onChange     (fn)      called with the new 1-indexed page number
 */
const Pagination = ({ page, totalPages, total, pageSize, onChange }) => {
  const safeTotalPages = Math.max(1, totalPages || 1);
  const canPrev = page > 1;
  const canNext = page < safeTotalPages;

  const go = (target) => {
    const clamped = Math.min(Math.max(1, target), safeTotalPages);
    if (clamped !== page) onChange(clamped);
  };

  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const btn =
    'inline-flex items-center justify-center w-9 h-9 rounded-lg border border-gray-200 text-gray-700 ' +
    'hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors';

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-6">
      <p className="text-sm text-gray-600">
        Showing <span className="font-semibold text-gray-900">{from}</span>–
        <span className="font-semibold text-gray-900">{to}</span> of{' '}
        <span className="font-semibold text-gray-900">{total}</span>
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={btn}
          onClick={() => go(1)}
          disabled={!canPrev}
          aria-label="First page"
        >
          <ChevronsLeft size={18} />
        </button>
        <button
          type="button"
          className={btn}
          onClick={() => go(page - 1)}
          disabled={!canPrev}
          aria-label="Previous page"
        >
          <ChevronLeft size={18} />
        </button>
        <span className="text-sm text-gray-700 px-2">
          Page <span className="font-semibold text-gray-900">{page}</span> of{' '}
          <span className="font-semibold text-gray-900">{safeTotalPages}</span>
        </span>
        <button
          type="button"
          className={btn}
          onClick={() => go(page + 1)}
          disabled={!canNext}
          aria-label="Next page"
        >
          <ChevronRight size={18} />
        </button>
        <button
          type="button"
          className={btn}
          onClick={() => go(safeTotalPages)}
          disabled={!canNext}
          aria-label="Last page"
        >
          <ChevronsRight size={18} />
        </button>
      </div>
    </div>
  );
};

export default Pagination;
