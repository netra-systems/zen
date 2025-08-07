import { StateUpdate } from '../../types/chat';

interface TodoListViewProps {
  todoList: StateUpdate;
}

export function TodoListView({ todoList }: TodoListViewProps) {
  return (
    <div className="mt-2">
      {todoList.todo_list.length > 0 && (
        <>
          <h4 className="font-bold">TODO</h4>
          <ul className="list-disc pl-5">
            {todoList.todo_list.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </>
      )}
      {todoList.completed_steps.length > 0 && (
        <>
          <h4 className="font-bold mt-2">Completed Steps</h4>
          <ul className="list-disc pl-5">
            {todoList.completed_steps.map((item, index) => (
              <li key={index} className="line-through">{item}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}