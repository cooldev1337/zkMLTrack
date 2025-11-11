<script>
  import { m } from '$lib/paraglide/messages.js';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
  import { buttonVariants } from '$lib/components/ui/button';
  import AccountLanguageSelector from '$lib/components/AccountLanguageSelector/index.svelte';
  import { LanguagesIcon } from '@lucide/svelte';
  import { cn } from '$lib/utils';

  let {
		align = 'end',
		variant = 'outline',
		class: className
	} = $props();
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger
		class={cn(buttonVariants({ variant, size: 'icon' }), className)}
		aria-label={m.changeLanguage()}
	>
		<LanguagesIcon class="size-4" />
		<span class="sr-only">{m.changeLanguage()}</span>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content {align} class="p-4 max-w-[100vw]">
    {m.ui_lang()}:
    <AccountLanguageSelector />
	</DropdownMenu.Content>
</DropdownMenu.Root>