<script module>
	import { m } from '$lib/paraglide/messages.js';
	import ListTodoIcon from "@lucide/svelte/icons/list-todo";

	const data = {
		navMain: [
			{
				title: m.dashboard_alltasks(),
				url: "/",
				icon: ListTodoIcon,
			},
		],
	};
</script>

<script>
	import NavMain from "./nav-main.svelte";
	import NavSecondary from "./nav-secondary.svelte";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import CommandIcon from "@lucide/svelte/icons/command";
	let { ref = $bindable(null), ...restProps } = $props();
</script>

<Sidebar.Root bind:ref variant="inset" {...restProps}>
	<Sidebar.Header>
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<div class="flex w-full items-center gap-2 p-2">
					<div
						class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg"
					>
						<CommandIcon class="size-4" />
					</div>
					<div class="grid flex-1 text-left text-sm leading-tight">
						<span class="truncate font-medium">zkMLTrack</span>
					</div>
				</div>
			</Sidebar.MenuItem>
		</Sidebar.Menu>
	</Sidebar.Header>
	<Sidebar.Content>
		<NavMain items={data.navMain} />
		<NavSecondary items={[]} class="mt-auto" />
	</Sidebar.Content>
</Sidebar.Root>