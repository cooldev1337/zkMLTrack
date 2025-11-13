<script>
  import { m } from '$lib/paraglide/messages';
  import { page } from '$app/state';
  import tasks from '$lib/tasks';
  let taskId = page.params.taskId;
  let error = $state(false);

  let task;

  for (let i = 0; i < tasks.length; i++) {
    if(tasks[i].id == taskId) {
      task = tasks[i];
      break;
    }
  }

  if(task == undefined || taskId < 0)
    error = true;
</script>

{#if error}
Task Not Found
{:else}
<h1 class="scroll-m-20 text-balance text-4xl font-extrabold tracking-tight">
  {task.name}
</h1>

{/if}