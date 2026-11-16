/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget"
import {renderToElement} from "@web/core/utils/render"
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.JobOfferPortalSubmit = publicWidget.Widget.extend({
    selector: '.oe_portal_job_offer_form',
    events: {
        'click button[type="submit"]': '_onSubmit',
    },


    async start() {

    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm")

    },

    async _onSubmit(event) {
        event.preventDefault();
        const $submitButton = this.$('button[type="submit"]');
        $submitButton.prop('disabled', true);

        const acceptOffer = this.$('#accept_offer').is(':checked');
        const rejectOffer = this.$('#reject_offer').is(':checked');
        const joinDate = this.$('#join_date').val();
        const rejectReason = this.$('#reject_reason').val();


        if(acceptOffer){
            var params = {
            'reject_reason':rejectReason,
            'availability_date':joinDate,
            'decision':'accept',
            };
        }
        if(rejectOffer){
           var params = {
            'reject_reason':rejectReason,
            'availability_date':joinDate,
            'decision':'reject',
            };
        }

        var $errorTarget = this.$('.o_job_offer_portal_error');
        var $errorTargetChild = this.$('.o_job_offer_portal_error  .p_job_offer_portal_error');
        var token = window.location.pathname.split('/').pop();
        var route = '/recruitment/offer/' + token + '/result';
        const submitPromise = await this.rpc(route, params);
        $submitButton.prop('disabled', false);
        if (!submitPromise.success){
                $errorTargetChild.text(submitPromise.errors)
                $errorTarget.removeClass('d-none');
        }
        else{
            window.location.href = '/application/thank_page';
        }

    },
});