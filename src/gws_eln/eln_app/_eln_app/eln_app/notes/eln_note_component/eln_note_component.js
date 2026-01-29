
import { DcHttpService } from '/external/gws_plugin/dc-reflex.js';
// CSS is loaded separately via rx.asset() in Python - don't import here
// as dynamic imports can't handle CSS in production builds


/**
 * Maps activity types to human-readable labels and Material Icons
 * (equivalents of the Lucide icons used in activity_type_component.py).
 */
const ACTIVITY_TYPE_CONFIG = {
  create: { label: 'Created', icon: 'add_box', color: 'var(--accent-9)' },
  receive: { label: 'Received', icon: 'inventory_2', color: 'var(--accent-9)' },
  move: { label: 'Moved', icon: 'arrow_forward', color: 'var(--accent-10)' },
  consume: { label: 'Consumed', icon: 'local_fire_department', color: 'var(--accent-11)' },
  use: { label: 'Used', icon: 'pan_tool', color: 'var(--accent-8)' },
  discard: { label: 'Discarded', icon: 'delete', color: 'var(--accent-12)' },
  aliquot: { label: 'Aliquot', icon: 'call_split', color: 'var(--accent-7)' },
  aliquot_created: { label: 'Aliquot creation', icon: 'arrow_downward', color: 'var(--accent-6)' },
  relabel: { label: 'Relabeled', icon: 'label', color: 'var(--accent-5)' },
};

/**
 * Factory function to create custom tools for the rich text editor.
 * @param {object} customToolsConfig - Configuration for custom blocks
 * @param {object} authenticationInfo - Authentication information passed from the component
 * @param {function} customToolsEvent - Callback for custom tool events
 * @returns {object} Custom tools configuration object
 */
export function getCustomTools(customToolsConfig, authenticationInfo, customToolsEvent) {

  if (!customToolsEvent) {
    throw new Error("customToolsEvent callback is required");
  }

  class DcTextEditorToolActivityBlock {
    static get toolbox() {
      return {
        title: 'Activity',
        icon: '<span class="material-icons-outlined">science</span>',
      }
    }

    constructor(editorJs) {
      this.api = editorJs.api;
      this.data = editorJs.data;
      this.editorJs = editorJs;
    }

    /**
     * Render the activity as a condensed inline card.
     */
    _renderCard(wrapper, activity) {
      const typeCfg = ACTIVITY_TYPE_CONFIG[activity.activity_type] || {
        label: activity.activity_type,
        icon: 'info',
        color: 'var(--gray-9)',
      };

      const card = document.createElement('div');
      card.className = 'ab-card';

      // --- Header ---
      const header = document.createElement('div');
      header.className = 'ab-header';

      const icon = document.createElement('span');
      icon.className = 'material-icons-outlined ab-header-icon';
      icon.textContent = typeCfg.icon;

      const title = document.createElement('span');
      title.className = 'ab-header-title';

      const typeText = document.createTextNode(`${typeCfg.label} — `);
      title.appendChild(typeText);

      const batchLink = document.createElement('a');
      batchLink.className = 'ab-batch-link';
      batchLink.textContent = activity.batch?.batch_number || 'Unknown batch';
      if (activity.batch?.id) {
        batchLink.href = `/batches/${activity.batch.id}`;
      }
      title.appendChild(batchLink);

      header.appendChild(icon);
      header.appendChild(title);

      if (activity.batch?.label) {
        const labelEl = document.createElement('span');
        labelEl.className = 'ab-header-label';
        labelEl.textContent = `– ${activity.batch.label}`;
        header.appendChild(labelEl);
      }
      card.appendChild(header);

      // --- Detail chips line ---
      const details = [];
      const type = activity.activity_type;

      if (['create', 'receive', 'consume', 'aliquot', 'aliquot_created'].includes(type)) {
        if (activity.pretty_quantity) {
          details.push(`Qty: ${activity.pretty_quantity}`);
        }
      }

      if (type === 'move') {
        if (activity.from_location?.name) {
          details.push(`From: ${activity.from_location.name}`);
        }
        if (activity.to_location?.name) {
          details.push(`To: ${activity.to_location.name}`);
        }
      }

      if (['create', 'receive'].includes(type)) {
        if (activity.to_location?.name) {
          details.push(`Location: ${activity.to_location.name}`);
        }
      }

      if (['aliquot', 'aliquot_created'].includes(type)) {
        if (activity.related_batch?.batch_number) {
          const relLabel = type === 'aliquot' ? 'Child' : 'Parent';
          details.push(`${relLabel}: ${activity.related_batch.batch_number}`);
        }
      }

      if (activity.created_by?.first_name) {
        const name = `${activity.created_by.first_name} ${activity.created_by.last_name || ''}`.trim();
        details.push(`By: ${name}`);
      }

      const hasBody = details.length > 0 || activity.notes;
      if (hasBody) {
        const body = document.createElement('div');
        body.className = 'ab-body';

        if (details.length > 0) {
          const detailLine = document.createElement('div');
          detailLine.className = 'ab-details';
          detailLine.textContent = details.join('  ·  ');
          body.appendChild(detailLine);
        }

        if (activity.notes) {
          const notesEl = document.createElement('div');
          notesEl.className = 'ab-notes';
          notesEl.textContent = activity.notes;
          body.appendChild(notesEl);
        }

        card.appendChild(body);
      }

      wrapper.innerHTML = '';
      wrapper.appendChild(card);
    }

    /**
     * Render the block — fetches activity data and displays the card.
     */
    render() {
      const wrapper = document.createElement('div');
      wrapper.className = 'activity-block';

      const loading = document.createElement('p');
      loading.className = 'ab-loading';
      loading.textContent = 'Loading activity…';
      wrapper.appendChild(loading);

      const activityId = this.data?.activity_id;
      if (!activityId) {
        loading.textContent = 'No activity ID provided.';
        return wrapper;
      }

      const httpService = new DcHttpService(
        authenticationInfo?.app_id || '',
        authenticationInfo?.user_access_token || '',
      );

      httpService.get(`${customToolsConfig.config.apiUrl}activity/${activityId}`, {
        headers: {
          'gws_user_access_token': authenticationInfo?.user_access_token || '',
          'gws_app_id': authenticationInfo?.app_id || '',
        },
      })
        .then(data => {
          this._renderCard(wrapper, data);
        })
        .catch(err => {
          console.error('Error fetching activity:', err);
          loading.textContent = 'Error loading activity.';
        });

      return wrapper;
    }

    save() {
      return { activity_id: this.data?.activity_id || '' };
    }

    // don't enable otherwise the new block will require an activity_id on creation
    // validate(blockData) {
    //   return blockData?.activity_id?.length > 0;
    // }

    /**
     * When a new block is appended, trigger an event to notify the system 
     * so it can open the activity selection dialog.
     */
    appendCallback() {
      this.editorJs.api.saver.save().then(
        richTextContent => {
          customToolsEvent({
            type: 'activity_block_appended',
            block_id: this.editorJs.block.id,
            richTextContent: richTextContent,
            detail: { message: 'Activity block was added.' },
          })
        }
      );
    }
  }

  return { [customToolsConfig.customBlocks.ActivityBlock]: DcTextEditorToolActivityBlock };
}