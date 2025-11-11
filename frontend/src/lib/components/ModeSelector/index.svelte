<script>
  import { m } from '$lib/paraglide/messages.js';
  import SunIcon from "@lucide/svelte/icons/sun";
  import MoonIcon from "@lucide/svelte/icons/moon";
 
  import { resetMode, setMode } from "mode-watcher";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import { buttonVariants } from "$lib/components/ui/button/index.js";
</script>
 
<DropdownMenu.Root>
  <DropdownMenu.Trigger
    class={buttonVariants({ variant: "outline", size: "icon" })}
  >
    <SunIcon
      class="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0"
    />
    <MoonIcon
      class="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100"
    />
    <span class="sr-only">{m.theme_toggle()}</span>
  </DropdownMenu.Trigger>
  <DropdownMenu.Content align="end">
    <DropdownMenu.Item onclick={() => setMode("light")}>{m.theme_light()}</DropdownMenu.Item
    >
    <DropdownMenu.Item onclick={() => setMode("dark")}>{m.theme_dark()}</DropdownMenu.Item>
    <DropdownMenu.Item onclick={() => resetMode()}>{m.theme_system()}</DropdownMenu.Item>
  </DropdownMenu.Content>
</DropdownMenu.Root>