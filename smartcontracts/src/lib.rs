#![cfg_attr(not(feature = "export-abi"), no_main)]
extern crate alloc;

use stylus_sdk::prelude::*;
use stylus_sdk::tx::{origin};
use stylus_sdk::{msg};
use stylus_sdk::alloy_primitives::{Address, U8, U64};
use stylus_sdk::storage::{StorageMap, StorageU64, StorageAddress};
use stylus_sdk::block;

#[storage]
pub struct VersionInfo {
  hash: [U8; 32],
  timestamp: StorageU64,
}

#[storage]
pub struct Task {
  latest_version: StorageU64,
  versions: StorageMap<U64, VersionInfo>,
}

#[storage]
#[entrypoint]
pub struct Registry {
  pub tasks: StorageMap<String, Task>,
  owner: StorageAddress,
}

#[public]
impl Registry {

  pub fn init(&mut self) {
    let origin = Address::from(origin());
    self.owner.set(origin);
  }

  fn assert_owner(&self) {
    let sender = Address::from(msg::sender());

    assert_eq!(
        sender,
        self.owner.get(),
        "only owner can call"
    );
  }

  pub fn register_task(&mut self, task_id: String) {
    self.assert_owner();
    assert!(
      !self.tasks.contains_key(&task_id),
      "task already registered"
    );
    let task = Task {
      latest_version: 1,
      versions: StorageMap::new(),
    };
    self.tasks.insert(task_id.clone(), task);
  }

  pub fn publish_new_version(
    &mut self,
    task_id: String,
    hash: [U8; 32],
  ) {
    self.assert_owner();
    let task = self
      .tasks
      .get_mut(&task_id)
      .expect("task not found");

    let new_ver = task.latest_version + 1;
    let info = VersionInfo {
      hash,
      timestamp: block::timestamp(),
    };

    task.versions.insert(new_ver, info);
    task.latest_version = new_ver;
  }

  pub fn get_latest(&self, task_id: String) -> VersionInfo {
    let task = self.tasks.get(&task_id).expect("task not found");
    task
      .versions
      .get(&task.latest_version)
      .expect("no versions yet")
      .clone()
  }
}