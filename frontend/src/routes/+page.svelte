<script>
  import { m } from "$lib/paraglide/messages";
  import { getLocale } from "$lib/paraglide/runtime";
  import * as Card from "$lib/components/ui/card/index.js";
  import tasks from "$lib/tasks";
</script>

<h1 class="scroll-m-20 text-balance text-4xl font-extrabold tracking-tight mb-4">
  {m.dashboard_alltasks()}
</h1>

<div class="flex gap-2 py-2">
  {#each tasks as task}
  <a href={`/tasks/${task.id}`}>
    <Card.Root class="w-md">
      <Card.Content>
        <strong>
          {getLocale().substring(0,2) == "es" ? task.nameEs : task.name}
        </strong>
        <p>
          {getLocale().substring(0,2) == "es" ? task.descriptionEs : task.description}
        </p>
      </Card.Content>
    </Card.Root>
  </a>
  {/each}
</div>