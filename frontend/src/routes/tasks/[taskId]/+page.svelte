<script>
  import { m } from '$lib/paraglide/messages';
  import { page } from '$app/state';
  import tasks from '$lib/tasks';
  import Button from '$lib/components/ui/button/button.svelte';
  import { backendHost } from '$lib/var';
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

  let file = $state(null);
  let uploading = $state(false);
  let progress = $state(0);

  function handleFileChange(e) {
    file = e.target?.files?.[0] ?? null;
  }

  function handleUpload() {
    if (!file) return;

    uploading = true;

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "localhost:2000/api/upload");

    // Track progress
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        progress = Math.round((e.loaded / e.total) * 100);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        console.log("File uploaded:", JSON.parse(xhr.responseText));
      } else {
        console.error(`Upload failed with status ${xhr.status}`);
      }
      uploading = false;
      progress = 0;
      file = null;
    };

    xhr.onerror = () => {
      console.error("Upload failed due to a network error");
      uploading = false;
      progress = 0;
    };

    xhr.send(formData);
  }
</script>

{#if error}
Task Not Found
{:else}
<h1 class="scroll-m-20 text-balance text-4xl font-extrabold tracking-tight">
  {task.name}
</h1>

<div class="flex flex-col gap-4 w-80">
  <form action={`${backendHost}/models`} method="post" encType="multipart/form-data">
    <input type="hidden" name="task_id" value={taskId} />
    <input type="file" name="model" required />

    <Button type="submit">
      Upload to test version
    </Button>
  </form>
</div>
{/if}