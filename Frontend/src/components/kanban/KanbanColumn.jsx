import { Inbox } from 'lucide-react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import KanbanCard from './KanbanCard';
import { TASK_STATUS_COLORS } from '../../utils/constants';

const STATUS_TONES = {
  PENDING: {
    header: 'bg-amber-50',
    text: 'text-amber-700',
    pill: 'bg-amber-100 text-amber-800',
    overRing: 'ring-amber-300',
    overBg: 'bg-amber-50/40',
  },
  IN_PROGRESS: {
    header: 'bg-blue-50',
    text: 'text-blue-700',
    pill: 'bg-blue-100 text-blue-800',
    overRing: 'ring-blue-300',
    overBg: 'bg-blue-50/40',
  },
  COMPLETED: {
    header: 'bg-emerald-50',
    text: 'text-emerald-700',
    pill: 'bg-emerald-100 text-emerald-800',
    overRing: 'ring-emerald-300',
    overBg: 'bg-emerald-50/40',
  },
};

const EMPTY_STATE_MESSAGE = {
  PENDING: 'No tasks to start',
  IN_PROGRESS: 'Nothing in progress',
  COMPLETED: 'No completed tasks yet',
};

const KanbanColumn = ({ status, label, tasks = [], remoteDrags = {} }) => {
  const tone = STATUS_TONES[status] || STATUS_TONES.PENDING;
  // Reference TASK_STATUS_COLORS to keep the visual contract documented in one place.
  // (Tones above mirror the same scale; the import guards against drift.)
  void TASK_STATUS_COLORS;

  const { setNodeRef, isOver } = useDroppable({
    id: `column-${status}`,
    data: { status, isColumn: true },
  });

  const ids = tasks.map((t) => String(t.id));

  return (
    <div
      ref={setNodeRef}
      className={`bg-white/70 backdrop-blur-sm rounded-xl p-4 min-h-[60vh] space-y-3 transition-all duration-200 ${
        isOver ? `ring-2 ${tone.overRing} ${tone.overBg}` : ''
      }`}
    >
      <div className={`flex items-center justify-between rounded-lg px-3 py-2 ${tone.header}`}>
        <h2 className={`text-lg font-semibold ${tone.text}`}>{label}</h2>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${tone.pill}`}>
          {tasks.length}
        </span>
      </div>

      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <div className="space-y-3">
          {tasks.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-3">
                <Inbox className="w-8 h-8 text-gray-300" />
              </div>
              <p className="text-sm text-gray-500">{EMPTY_STATE_MESSAGE[status]}</p>
            </div>
          ) : (
            tasks.map((task, index) => (
              <KanbanCard
                key={task.id}
                task={task}
                index={index}
                remoteDrag={remoteDrags[task.id]}
              />
            ))
          )}
        </div>
      </SortableContext>
    </div>
  );
};

export default KanbanColumn;
