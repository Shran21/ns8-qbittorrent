<!--
  Copyright (C) 2022 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-form @submit.prevent="configureModule">
            <cv-text-input
              :label="$t('settings.qbittorrent_fqdn')"
              placeholder="qbittorrent.example.org"
              v-model.trim="host"
              class="mg-bottom"
              :invalid-message="$t(error.host)"
              :disabled="loading.getConfiguration || loading.configureModule"
              ref="host"
            >
            </cv-text-input>
            <cv-toggle
              value="letsEncrypt"
              :label="$t('settings.lets_encrypt')"
              v-model="isLetsEncryptEnabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="mg-bottom"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </cv-toggle>
            <cv-toggle
              value="httpToHttps"
              :label="$t('settings.http_to_https')"
              v-model="isHttpToHttpsEnabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="mg-bottom"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </cv-toggle>
            <!-- BitTorrent connectivity -->
            <h6 class="section-title">{{ $t("settings.connectivity") }}</h6>
            <cv-toggle
              value="btPortEnabled"
              :label="$t('settings.bt_port_enabled')"
              v-model="isBtPortEnabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="mg-bottom"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </cv-toggle>
            <cv-number-input
              :label="$t('settings.bt_port')"
              :helper-text="$t('settings.bt_port_helper')"
              v-model="btPort"
              class="mg-bottom maxwidth"
              :invalid-message="$t(error.bt_port)"
              :disabled="loading.getConfiguration || loading.configureModule"
              :min="1024"
              :max="65535"
              :step="1"
              ref="bt_port"
            >
            </cv-number-input>
            <!-- advanced options -->
            <cv-accordion ref="accordion" class="maxwidth mg-bottom">
              <cv-accordion-item :open="false">
                <template slot="title">{{ $t("settings.advanced") }}</template>
                <template slot="content">
                  <cv-text-input
                    :label="$t('settings.downloads_dir')"
                    :helper-text="$t('settings.downloads_dir_helper')"
                    placeholder="/data/qbittorrent/downloads"
                    v-model.trim="downloadsDir"
                    class="mg-bottom"
                    :invalid-message="$t(error.downloads_dir)"
                    :disabled="
                      loading.getConfiguration || loading.configureModule
                    "
                    ref="downloads_dir"
                  >
                  </cv-text-input>
                  <cv-text-input
                    :label="$t('settings.timezone')"
                    :helper-text="$t('settings.timezone_helper')"
                    placeholder="Europe/Budapest"
                    v-model.trim="timezone"
                    class="mg-bottom"
                    :invalid-message="$t(error.timezone)"
                    :disabled="
                      loading.getConfiguration || loading.configureModule
                    "
                    ref="timezone"
                  >
                  </cv-text-input>
                  <cv-text-input
                    :label="$t('settings.umask')"
                    :helper-text="$t('settings.umask_helper')"
                    placeholder="002"
                    v-model.trim="umask"
                    class="mg-bottom"
                    :invalid-message="$t(error.umask)"
                    :disabled="
                      loading.getConfiguration || loading.configureModule
                    "
                    ref="umask"
                  >
                  </cv-text-input>
                </template>
              </cv-accordion-item>
            </cv-accordion>
            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="loading.getConfiguration || loading.configureModule"
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

const DEFAULT_BT_PORT = 6881;

export default {
  name: "Settings",
  mixins: [
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      host: "",
      downloadsDir: "",
      btPort: DEFAULT_BT_PORT,
      isBtPortEnabled: true,
      umask: "002",
      timezone: "UTC",
      isLetsEncryptEnabled: false,
      isHttpToHttpsEnabled: true,
      loading: {
        getConfiguration: false,
        configureModule: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        downloads_dir: "",
        bt_port: "",
        bt_port_enabled: "",
        umask: "",
        timezone: "",
        lets_encrypt: "",
        http2https: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
  },
  created() {
    this.getConfiguration();
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  methods: {
    async getConfiguration() {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getConfigurationCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`, err);
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
        return;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      const config = taskResult.output;
      this.host = config.host;
      // An empty downloads_dir means the qbittorrent-downloads named
      // volume is in use: keep the field empty so that saving the form
      // does not silently turn it into a bind mount.
      this.downloadsDir = config.downloads_dir || "";
      this.btPort = config.bt_port || DEFAULT_BT_PORT;
      this.isBtPortEnabled = config.bt_port_enabled;
      this.umask = config.umask;
      this.timezone = config.timezone;
      this.isLetsEncryptEnabled = config.lets_encrypt;
      this.isHttpToHttpsEnabled = config.http2https;

      this.loading.getConfiguration = false;
      this.focusElement("host");
    },
    validateConfigureModule() {
      this.clearErrors(this);

      let isValidationOk = true;
      let focusAlreadySet = false;

      const setError = (field, message) => {
        this.error[field] = message;
        if (!focusAlreadySet) {
          this.focusElement(field);
          focusAlreadySet = true;
        }
        isValidationOk = false;
      };

      if (!this.host) {
        setError("host", "common.required");
      }

      // cv-number-input emits NaN, not "", when the value is cleared
      const btPort = Number(this.btPort);
      if (!Number.isInteger(btPort) || btPort < 1024 || btPort > 65535) {
        setError("bt_port", "settings.bt_port_invalid");
      }

      if (
        this.downloadsDir &&
        !/^\/[A-Za-z0-9._@+-]+(\/[A-Za-z0-9._@+-]+)*$/.test(this.downloadsDir)
      ) {
        setError("downloads_dir", "settings.downloads_dir_invalid");
      }

      if (!/^[0-7]{3,4}$/.test(this.umask)) {
        setError("umask", "settings.umask_invalid");
      }

      if (!this.timezone) {
        setError("timezone", "common.required");
      }

      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const param = validationError.parameter;
        // set i18n error message
        this.error[param] = this.$t("settings." + validationError.error);

        if (!focusAlreadySet) {
          this.focusElement(param);
          focusAlreadySet = true;
        }
      }
    },
    async configureModule() {
      const isValidationOk = this.validateConfigureModule();
      if (!isValidationOk) {
        return;
      }

      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );

      // register to task validation
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );
      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            host: this.host,
            downloads_dir: this.downloadsDir,
            bt_port: Number(this.btPort),
            bt_port_enabled: this.isBtPortEnabled,
            umask: this.umask,
            timezone: this.timezone,
            lets_encrypt: this.isLetsEncryptEnabled,
            http2https: this.isHttpToHttpsEnabled,
          },
          extra: {
            title: this.$t("settings.instance_configuration", {
              instance: this.instanceName,
            }),
            description: this.$t("settings.configuring"),
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`, err);
        this.error.configureModule = this.getErrorMessage(err);
        this.loading.configureModule = false;
        return;
      }
    },
    configureModuleAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
.mg-bottom {
  margin-bottom: $spacing-06;
}

.maxwidth {
  max-width: 38rem;
}

.section-title {
  margin-bottom: $spacing-05;
}
</style>
