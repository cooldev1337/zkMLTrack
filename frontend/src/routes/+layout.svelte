<script>
	import AppSidebar from "$lib/components/app-sidebar.svelte";
	import { Separator } from "$lib/components/ui/separator/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import AccountLanguageDropdown from "$lib/components/AccountLanguageDropdown/index.svelte";
	import ModeSelector from "$lib/components/ModeSelector/index.svelte";
	import { ModeWatcher } from "mode-watcher";
	import { Toaster } from "$lib/components/ui/sonner/index.js";
	import '../app.css';

	let { children } = $props();
</script>

<ModeWatcher />
<Toaster richColors duration={10000} closeButton />

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<header class="flex h-16 shrink-0 items-center gap-2">
			<div class="flex items-center gap-2 px-4 w-full">
				<Sidebar.Trigger class="-ml-1" />
				<Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />
				<div class="flex gap-1 flex-wrap flex-row ml-auto">
					<AccountLanguageDropdown />
					<ModeSelector />
				</div>
			</div>
		</header>
		<div class="p-4 pt-0 flex flex-col flex-grow">
			{@render children()}
		</div>
	</Sidebar.Inset>
</Sidebar.Provider>