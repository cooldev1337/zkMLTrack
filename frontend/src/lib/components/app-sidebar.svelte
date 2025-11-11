<script module>
	import { m } from '$lib/paraglide/messages.js';
	import HandCoinsIcon from "@lucide/svelte/icons/hand-coins";
	import Settings2Icon from "@lucide/svelte/icons/settings-2";
	import AudioLinesIcon from "@lucide/svelte/icons/audio-lines";
	import UserPenIcon from "@lucide/svelte/icons/user-pen";
	import VideoIcon from "@lucide/svelte/icons/video";

	const data = {
		navMain: [
			{
				title: m.dashboard_allvideos(),
				url: "/",
				icon: Settings2Icon,
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