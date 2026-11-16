odoo.define('nt_penalty_and_reward.BasicView', function (require) {
"use strict";

var session = require('web.session');
var BasicView = require('web.BasicView');
BasicView.include({
        init: function(viewInfo, params) {
            var self = this;
            this._super.apply(this, arguments);
            var model = self.controllerParams.modelName in ['employee.penalty.reward'] ? 'True' : 'False';
            if(model) {
                session.user_has_group('nt_penalty_and_reward.group_penalty_reward_admin').then(function(has_group) {
                    if(!has_group) {
                        self.controllerParams.archiveEnabled = 'False' in viewInfo.fields;
                    }
                });
            }
        },
});
});